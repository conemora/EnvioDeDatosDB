
import csv
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Semilla para generar datos reproducibles
random.seed(105)

# Ubicación de los archivos CSV
data = Path(__file__).resolve().parent.parent / "data"
data.mkdir(exist_ok=True)

comunas = [
    "Talca", "Curicó", "Linares",
    "San Clemente", "Molina", "Parral",
    "San Javier", "Constitución",
    "Cauquenes", "Maule"
]

materiales = [
    "vidrio", "papel", "carton",
    "plastico", "metal"
]

transportistas = [
    "Ruta Verde",
    "EcoTrans",
    "Maule Circular"
]

puntos = []
retiros = []

# Generar 30 puntos limpios
for i in range(1, 31):

    comuna = comunas[(i - 1) % len(comunas)]

    punto = {
        "punto_id": f"PL-{i:03d}",
        "nombre": f"Punto Limpio {comuna} {i}",
        "comuna": comuna,
        "region": "Maule",
        "capacidad_kg": random.randint(500, 2500),
        "estado": random.choice([
            "activo", "mantencion"
        ]),
        "materiales": "|".join(
            random.sample(materiales, 3)
        )
    }

    puntos.append(punto)

# Fecha inicial de los retiros
fecha_base = datetime(
    2026, 10, 1, 8, 0,
    tzinfo=timezone.utc
)

# Generar 1000 retiros
for i in range(1, 1001):

    punto = puntos[(i - 1) % len(puntos)]

    retiro = {
        "retiro_id": f"RET-{i:04d}",
        "punto_id": punto["punto_id"],
        "fecha_retiro": (
            fecha_base + timedelta(hours=i)
        ).isoformat(),
        "material": random.choice(
            punto["materiales"].split("|")
        ),
        "kg": round(random.uniform(5, 200), 2),
        "transportista": random.choice(
            transportistas
        ),
        "estado": random.choice([
            "recibido",
            "validado",
            "observado"
        ])
    }

    retiros.append(retiro)

# Función para guardar los archivos CSV
def guardar_csv(nombre, registros):

    with open(
        data / nombre,
        "w",
        newline="",
        encoding="utf-8"
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=registros[0].keys()
        )

        escritor.writeheader()
        escritor.writerows(registros)

# Crear ambos archivos
guardar_csv("puntos_limpios.csv", puntos)
guardar_csv("retiros.csv", retiros)

print("Archivos generados correctamente")
print("Puntos limpios:", len(puntos))
print("Retiros:", len(retiros))
