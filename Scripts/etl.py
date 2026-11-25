import os
from pathlib import Path

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

# Programa principal
def main():
    try:
        with conectar_postgresql() as pg:

            print("Conexion exitosa con PostgreSQL")

            # Extraccion de datos
            puntos = extraer_puntos_limpios(pg)
            retiros = extraer_retiros(pg)

            print("\n--- EXTRACCION DE DATOS ---")
            print("Puntos extraidos:", len(puntos))
            print("Retiros extraidos:", len(retiros))

            # Mostrar ejemplos
            if puntos:
                print("\nPrimer punto limpio:")
                print(puntos[0])

            if retiros:
                print("\nPrimer retiro:")
                print(retiros[0])

        with conectar_mongodb() as mongo:

            print("\nConexion exitosa con MongoDB Atlas")

            db = mongo[os.getenv("MONGO_DATABASE")]

            print("Base de datos:", db.name)
            print("Colecciones:", db.list_collection_names())

        print("\nExtraccion finalizada correctamente")

    except Exception as error:
        print("Error:", type(error).__name__)
        raise SystemExit(1)


if __name__ == "__main__":
    main()