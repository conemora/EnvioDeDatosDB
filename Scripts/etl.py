import os
from pathlib import Path

import logging
import time

from datetime import datetime, timezone
from bson.decimal128 import Decimal128
from decimal import Decimal

from psycopg.rows import dict_row
from pymongo import MongoClient, UpdateOne

import psycopg
from pymongo import MongoClient
from dotenv import load_dotenv

# Cargar las variables de entorno
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Configuracion de logs
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "etl.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# Conexion a PostgreSQL
def conectar_postgresql():
    conexion = psycopg.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        connect_timeout=10
    )

    return conexion


# Conexion a MongoDB Atlas
def conectar_mongodb():
    cliente = MongoClient(
        os.getenv("MONGO_URI"),
        serverSelectionTimeoutMS=10000
    )

    try:
        cliente.admin.command("ping")
        return cliente
    except Exception:
        cliente.close()
        raise

# Extraer puntos limpios desde PostgreSQL
def extraer_puntos_limpios(pg):

    with pg.cursor(row_factory=dict_row) as cursor:

        cursor.execute("""
            SELECT
                punto_id,
                nombre,
                comuna,
                region,
                capacidad_kg,
                estado,
                materiales
            FROM public.puntos_limpios
            ORDER BY punto_id;
        """)

        puntos = cursor.fetchall()

    return puntos

# Extraer retiros desde PostgreSQL
def extraer_retiros(pg):

    with pg.cursor(row_factory=dict_row) as cursor:

        cursor.execute("""
            SELECT
                retiro_id,
                punto_id,
                fecha_retiro,
                material,
                kg,
                transportista,
                estado
            FROM public.retiros
            ORDER BY retiro_id;
        """)

        retiros = cursor.fetchall()

    return retiros

# Transformar y validar puntos limpios
def transformar_puntos(puntos):

    validos = []
    rechazados = []
    ids = set()

    for punto in puntos:

        try:
            if not punto["punto_id"]:
                raise ValueError("Identificador vacio")

            if punto["punto_id"] in ids:
                raise ValueError("Identificador duplicado")

            if punto["capacidad_kg"] <= 0:
                raise ValueError("Capacidad incorrecta")

            if punto["estado"] not in ["activo", "mantencion"]:
                raise ValueError("Estado incorrecto")

            documento = dict(punto)

            documento["materiales"] = [
                material.strip().lower()
                for material in punto["materiales"].split("|")
                if material.strip()
            ]

            if not documento["materiales"]:
                raise ValueError("Materiales vacios")

            documento["fuente"] = (
                "postgresql.ecoruta_origen.public.puntos_limpios"
            )

            validos.append(documento)
            ids.add(punto["punto_id"])

        except (ValueError, TypeError, KeyError) as error:
            rechazados.append({
                "punto_id": punto.get("punto_id"),
                "motivo": str(error)
            })

    return validos, rechazados

# Transformar y validar retiros
def transformar_retiros(retiros, puntos_validos):

    validos = []
    rechazados = []
    ids = set()

    ids_puntos = {
        punto["punto_id"]
        for punto in puntos_validos
    }

    for retiro in retiros:

        try:
            if not retiro["retiro_id"]:
                raise ValueError("Identificador vacio")

            if retiro["retiro_id"] in ids:
                raise ValueError("Identificador duplicado")

            if retiro["punto_id"] not in ids_puntos:
                raise ValueError("Punto limpio inexistente")

            kg = Decimal(str(retiro["kg"]))

            if not kg.is_finite() or kg <= 0:
                raise ValueError("Kilogramos incorrectos")

            if retiro["estado"] not in [
                "recibido", "validado", "observado"
            ]:
                raise ValueError("Estado incorrecto")

            fecha = retiro["fecha_retiro"]

            if not isinstance(fecha, datetime):
                raise ValueError("Fecha incorrecta")

            if fecha.utcoffset() is None:
                raise ValueError("Fecha sin zona horaria")

            documento = dict(retiro)

            documento["kg"] = Decimal128(kg)

            documento["fecha_retiro"] = fecha.astimezone(
                timezone.utc
            )

            documento["material"] = (
                retiro["material"].strip().lower()
            )

            documento["fuente"] = (
                "postgresql.ecoruta_origen.public.retiros"
            )

            validos.append(documento)
            ids.add(retiro["retiro_id"])

        except (ValueError, TypeError, KeyError, ArithmeticError) as error:
            rechazados.append({
                "retiro_id": retiro.get("retiro_id"),
                "motivo": str(error)
            })

    return validos, rechazados
# Crear indices unicos en MongoDB
def crear_indices(db):

    db.puntos_limpios.create_index(
        "punto_id",
        unique=True
    )

    db.retiros.create_index(
        "retiro_id",
        unique=True
    )

    print("Indice unico de puntos limpios creado")
    print("Indice unico de retiros creado")

# Verificar indices de MongoDB
def verificar_indices(db):

    print("\n--- INDICES DE PUNTOS LIMPIOS ---")

    for indice in db.puntos_limpios.list_indexes():
        print(indice)

    print("\n--- INDICES DE RETIROS ---")

    for indice in db.retiros.list_indexes():
        print(indice)

# Cargar documentos mediante bulk_write y upsert
def cargar_documentos(coleccion, documentos, campo_id):

    if not documentos:
        logger.warning("No hay documentos para cargar")
        return

    operaciones = []

    for documento in documentos:

        operacion = UpdateOne(
            {campo_id: documento[campo_id]},
            {"$set": documento},
            upsert=True
        )

        operaciones.append(operacion)

    resultado = coleccion.bulk_write(
        operaciones,
        ordered=False
    )

    logger.info("Coleccion: %s", coleccion.name)
    logger.info("Documentos procesados: %s", len(documentos))
    logger.info("Documentos insertados: %s", resultado.upserted_count)
    logger.info("Documentos encontrados: %s", resultado.matched_count)
    logger.info("Documentos modificados: %s", resultado.modified_count)

    return resultado

# Programa principal
def main():

    inicio = time.perf_counter()

    logger.info("========== INICIO DEL ETL ==========")

    try:

        # EXTRACCION
        with conectar_postgresql() as pg:

            pg.read_only = True

            logger.info("Conexion exitosa con PostgreSQL")

            puntos = extraer_puntos_limpios(pg)
            retiros = extraer_retiros(pg)

            logger.info("--- EXTRACCION ---")
            logger.info("Puntos extraidos: %s", len(puntos))
            logger.info("Retiros extraidos: %s", len(retiros))

        # TRANSFORMACION
        puntos_validos, puntos_rechazados = (
            transformar_puntos(puntos)
        )

        retiros_validos, retiros_rechazados = (
            transformar_retiros(retiros, puntos_validos)
        )

        logger.info("--- TRANSFORMACION ---")

        logger.info("Puntos validos: %s", len(puntos_validos))
        logger.info("Puntos rechazados: %s", len(puntos_rechazados))

        logger.info("Retiros validos: %s", len(retiros_validos))
        logger.info("Retiros rechazados: %s", len(retiros_rechazados))

        for rechazo in puntos_rechazados:
            logger.warning("Punto rechazado: %s", rechazo)

        for rechazo in retiros_rechazados:
            logger.warning("Retiro rechazado: %s", rechazo)

        # CARGA
        with conectar_mongodb() as mongo:

            logger.info("Conexion exitosa con MongoDB Atlas")

            db = mongo[os.getenv("MONGO_DATABASE")]

            logger.info("--- CREACION DE INDICES ---")

            crear_indices(db)

            logger.info("--- CARGA EN MONGODB ---")

            cargar_documentos(
                db.puntos_limpios,
                puntos_validos,
                "punto_id"
            )

            cargar_documentos(
                db.retiros,
                retiros_validos,
                "retiro_id"
            )

            # CONTEOS
            logger.info("--- CONTEO FINAL ---")

            logger.info(
                "Total puntos limpios: %s",
                db.puntos_limpios.count_documents({})
            )

            logger.info(
                "Total retiros: %s",
                db.retiros.count_documents({})
            )

        logger.info("ETL finalizado correctamente")

    except Exception as error:

        logger.error("Error durante el ETL: %s", type(error).__name__)

        raise SystemExit(1)

    finally:

        duracion = time.perf_counter() - inicio

        logger.info("Tiempo de ejecucion: %.2f segundos", duracion)
        logger.info("========== FIN DEL ETL ==========")


if __name__ == "__main__":
    main()