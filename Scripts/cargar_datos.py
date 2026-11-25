
import psycopg
from pathlib import Path
from getpass import getpass

# Ubicacion de los archivos CSV
data = Path(__file__).resolve().parent.parent / "data"

# Solicitar contraseña
password = getpass("Contraseña de PostgreSQL: ")

# Conexion con PostgreSQL
with psycopg.connect(
    host="127.0.0.1",
    port=5432,
    dbname="ecoruta_origen",
    user="ecoruta_g01",
    password=password,
    sslmode="prefer"
) as conexion:

    print("Conexion exitosa con PostgreSQL")

    with conexion.cursor() as cursor:

        # Importar puntos limpios
        with open(
            data / "puntos_limpios.csv",
            encoding="utf-8"
        ) as archivo:

            with cursor.copy("""
                COPY public.puntos_limpios (
                    punto_id,
                    nombre,
                    comuna,
                    region,
                    capacidad_kg,
                    estado,
                    materiales
                )
                FROM STDIN
                WITH (FORMAT CSV, HEADER TRUE)
            """) as copia:

                copia.write(archivo.read())

        print("Puntos limpios importados")

        # Importar retiros
        with open(
            data / "retiros.csv",
            encoding="utf-8"
        ) as archivo:

            with cursor.copy("""
                COPY public.retiros (
                    retiro_id,
                    punto_id,
                    fecha_retiro,
                    material,
                    kg,
                    transportista,
                    estado
                )
                FROM STDIN
                WITH (FORMAT CSV, HEADER TRUE)
            """) as copia:

                copia.write(archivo.read())

        print("Retiros importados")

    conexion.commit()

print("Datos importados correctamente")
