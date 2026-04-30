import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from scraper import obtener_actividades

DATA_DIR = "data"
RSS_DIR = "rss"
VISTAS_FILE = os.path.join(DATA_DIR, "vistas.json")
CEP_URL = "https://secretariavirtual.juntadeandalucia.es/secretariavirtual/consultaCEP/"


def cargar_vistas():
    if not os.path.exists(VISTAS_FILE):
        return {}
    with open(VISTAS_FILE, encoding="utf-8") as f:
        return json.load(f)


def guardar_vistas(vistas):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(VISTAS_FILE, "w", encoding="utf-8") as f:
        json.dump(vistas, f, ensure_ascii=False, indent=2)


def fecha_rss(iso_str):
    """Convierte fecha ISO a formato RFC 2822 que usa RSS."""
    dt = datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def generar_xml(nombre_canal, descripcion, actividades, vistas):
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = nombre_canal
    SubElement(channel, "link").text = CEP_URL
    SubElement(channel, "description").text = descripcion
    SubElement(channel, "language").text = "es"
    SubElement(channel, "lastBuildDate").text = fecha_rss(datetime.now(timezone.utc).isoformat())

    for a in actividades:
        codigo = a.get("Código", "")
        item = SubElement(channel, "item")
        SubElement(item, "title").text = f"{codigo} — {a.get('Título', '')}"
        SubElement(item, "description").text = (
            f"{a.get('CEP', '')} | {a.get('Modalidad', '')} | "
            f"{a.get('Inicio', '')} → {a.get('Fin', '')} | "
            f"Dirigido a: {a.get('Dirigido a', '')} | "
            f"Estado: {a.get('Estado', '')}"
        )
        SubElement(item, "link").text = CEP_URL
        SubElement(item, "guid", isPermaLink="false").text = codigo
        SubElement(item, "pubDate").text = fecha_rss(vistas[codigo])

    xml_str = tostring(rss, encoding="unicode")
    return minidom.parseString(xml_str).toprettyxml(indent="  ")


def generar_rss(estados=None):
    if estados is None:
        estados = ["6"]  # Por defecto: solo plazo abierto

    print("Scrapeando actividades...")
    todas = []
    for estado in estados:
        actividades = obtener_actividades({"estado": estado})
        print(f"  estado={estado}: {len(actividades)} actividades")
        todas.extend(actividades)

    # Eliminar duplicados por código
    vistas_cod = {}
    for a in todas:
        cod = a.get("Código", "")
        if cod and cod not in vistas_cod:
            vistas_cod[cod] = a
    todas = list(vistas_cod.values())

    # Registrar fecha de primera aparición
    vistas = cargar_vistas()
    ahora = datetime.now(timezone.utc).isoformat()
    nuevas = 0
    for a in todas:
        cod = a.get("Código", "")
        if cod and cod not in vistas:
            vistas[cod] = ahora
            nuevas += 1
    guardar_vistas(vistas)
    print(f"Actividades nuevas detectadas: {nuevas}")

    # Agrupar por CEP
    por_cep = defaultdict(list)
    for a in todas:
        por_cep[a.get("CEP", "Sin CEP")].append(a)

    os.makedirs(RSS_DIR, exist_ok=True)

    # Un fichero RSS por CEP
    for cep, actividades in sorted(por_cep.items()):
        nombre_cep = cep.split(" - ")[-1].strip() if " - " in cep else cep
        nombre_fichero = nombre_cep.lower().replace(" ", "_").replace("/", "-")
        ruta = os.path.join(RSS_DIR, f"{nombre_fichero}.xml")

        xml = generar_xml(
            nombre_canal=f"Actividades {nombre_cep}",
            descripcion=f"Actividades formativas con plazo abierto del {nombre_cep}",
            actividades=actividades,
            vistas=vistas,
        )
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(xml)

    # Fichero RSS con todas las actividades
    ruta_todas = os.path.join(RSS_DIR, "todas.xml")
    xml_todas = generar_xml(
        nombre_canal="Actividades CEP Andalucía",
        descripcion="Todas las actividades formativas con plazo abierto de los CEP de Andalucía",
        actividades=todas,
        vistas=vistas,
    )
    with open(ruta_todas, "w", encoding="utf-8") as f:
        f.write(xml_todas)

    print(f"\nFicheros RSS generados en '{RSS_DIR}/':")
    for f in sorted(os.listdir(RSS_DIR)):
        ruta = os.path.join(RSS_DIR, f)
        cep_nombre = f.replace(".xml", "").replace("_", " ").title()
        n = len([a for a in todas if cep_nombre.lower() in a.get("CEP", "").lower()]) if f != "todas.xml" else len(todas)
        print(f"  {f} ({n} actividades)")


if __name__ == "__main__":
    generar_rss()
