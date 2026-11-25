import os
from pathlib import Path

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


# Programa principal
def main():
    try:
        with conectar_postgresql() as pg:
            print("Conexion exitosa con PostgreSQL")

            with pg.cursor() as cursor:
                cursor.execute(
                    "SELECT current_database(), current_user;"
                )

                base, usuario = cursor.fetchone()

                print("Base de datos:", base)
                print("Usuario:", usuario)

        with conectar_mongodb() as mongo:
            print("Conexion exitosa con MongoDB Atlas")

            db = mongo[os.getenv("MONGO_DATABASE")]

            print("Base de datos:", db.name)
            print("Colecciones:", db.list_collection_names())

        print("Ambas conexiones funcionan correctamente")

    except Exception as error:
        print("Error de conexion:", type(error).__name__)
        raise SystemExit(1)


if __name__ == "__main__":
    main()