import os
from pathlib import Path

from datetime import datetime, timezone
from bson.decimal128 import Decimal128
from decimal import Decimal

from psycopg.rows import dict_row

import psycopg
from pymongo import MongoClient
from dotenv import load_dotenv

# Cargar las variables de entorno
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


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

# Programa principal
def main():

    try:
        with conectar_postgresql() as pg:

            pg.read_only = True

            print("Conexion exitosa con PostgreSQL")

            # EXTRACCION
            puntos = extraer_puntos_limpios(pg)
            retiros = extraer_retiros(pg)

            print("\n--- EXTRACCION ---")
            print("Puntos extraidos:", len(puntos))
            print("Retiros extraidos:", len(retiros))

        # TRANSFORMACION
        puntos_validos, puntos_rechazados = (
            transformar_puntos(puntos)
        )

        retiros_validos, retiros_rechazados = (
            transformar_retiros(retiros, puntos_validos)
        )

        print("\n--- TRANSFORMACION ---")

        print("Puntos validos:", len(puntos_validos))
        print("Puntos rechazados:", len(puntos_rechazados))

        print("Retiros validos:", len(retiros_validos))
        print("Retiros rechazados:", len(retiros_rechazados))

        if puntos_validos:
            print("\nEjemplo de punto transformado:")
            print(puntos_validos[0])

        if retiros_validos:
            print("\nEjemplo de retiro transformado:")
            print(retiros_validos[0])

        if puntos_rechazados:
            print("\nPuntos rechazados:")
            print(puntos_rechazados)

        if retiros_rechazados:
            print("\nRetiros rechazados:")
            print(retiros_rechazados)

        with conectar_mongodb() as mongo:

            print("\nConexion exitosa con MongoDB Atlas")

            db = mongo[os.getenv("MONGO_DATABASE")]

            print("Base de datos:", db.name)
            print("Colecciones:", db.list_collection_names())

        print("\nTransformacion finalizada correctamente")

    except Exception as error:
        print("Error:", type(error).__name__)
        raise SystemExit(1)


if __name__ == "__main__":
    main()