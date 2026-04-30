"""
Descarga las actividades del portal CEP y actualiza data/actividades.json
y data/vistas.json (registro de primera aparición de cada actividad).
"""
import json
import os
from datetime import datetime, timezone

from scraper import obtener_actividades

DATA_DIR = "data"
ACTIVIDADES_FILE = os.path.join(DATA_DIR, "actividades.json")
VISTAS_FILE = os.path.join(DATA_DIR, "vistas.json")

# Inicio del curso académico actual — limita resultados en estados con historial largo
FECHA_INICIO_CURSO = "01/09/2025"

# Estados a recoger. Los marcados con fecha_minima aplican filtro de fechaI.
ESTADOS = [
    {"id": "5",  "nombre": "En proyecto",                      "fecha_minima": False},
    {"id": "6",  "nombre": "Abierto plazo solicitudes",        "fecha_minima": False},
    {"id": "7",  "nombre": "Finalizado plazo solicitudes",     "fecha_minima": False},
    {"id": "2",  "nombre": "Actividad en desarrollo",          "fecha_minima": False},
    {"id": "4",  "nombre": "Publicadas Listas Provisionales",  "fecha_minima": True},
    {"id": "8",  "nombre": "Publicadas Listas Definitivas",    "fecha_minima": True},
]


def cargar_json(ruta):
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_json(ruta, datos):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def recoger_actividades():
    todas = {}

    for estado in ESTADOS:
        print(f"  Scrapeando: {estado['nombre']}...")
        try:
            filtros = {"estado": estado["id"]}
            if estado["fecha_minima"]:
                filtros["fechaI"] = FECHA_INICIO_CURSO
            actividades = obtener_actividades(filtros)
            for a in actividades:
                cod = a.get("Código", "")
                if cod:
                    todas[cod] = a
            print(f"    {len(actividades)} actividades")
        except Exception as e:
            print(f"    Error: {e}")

    return list(todas.values())


def main():
    print("=== Recolección de actividades CEP ===\n")

    actividades = recoger_actividades()
    print(f"\nTotal único: {len(actividades)} actividades\n")

    # Registrar fecha de primera aparición
    vistas = cargar_json(VISTAS_FILE)
    ahora = datetime.now(timezone.utc).isoformat()
    nuevas = []
    for a in actividades:
        cod = a.get("Código", "")
        if cod and cod not in vistas:
            vistas[cod] = ahora
            nuevas.append(a)

    guardar_json(VISTAS_FILE, vistas)
    print(f"Actividades nuevas detectadas: {len(nuevas)}")
    for a in nuevas[:5]:
        print(f"  + {a['Código']} — {a['Título'][:60]}")
    if len(nuevas) > 5:
        print(f"  ... y {len(nuevas) - 5} más")

    # Guardar datos con metadatos
    datos = {
        "generado": ahora,
        "total": len(actividades),
        "actividades": actividades,
    }
    guardar_json(ACTIVIDADES_FILE, datos)
    print(f"\nGuardado en {ACTIVIDADES_FILE}")


if __name__ == "__main__":
    main()
