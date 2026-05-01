"""
Lee data/actividades.json y genera:
  - docs/index.html  (web pública)
  - docs/rss/todas.xml
  - docs/rss/{cep_slug}.xml  (uno por CEP)
"""
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

DATA_DIR = "data"
DOCS_DIR = "docs"
RSS_DIR = os.path.join(DOCS_DIR, "rss")
CEP_URL = "https://secretariavirtual.juntadeandalucia.es/secretariavirtual/consultaCEP/"

PROVINCIA_NOMBRE = {
    "04": "ALMERÍA",  "11": "CÁDIZ",   "14": "CÓRDOBA", "18": "GRANADA",
    "21": "HUELVA",   "23": "JAÉN",    "29": "MÁLAGA",  "41": "SEVILLA",
}

BADGE_COLOR = {
    "Abierto plazo solicitudes":       "#E76F51",  # énfasis — acción inmediata
    "En proyecto":                     "#15616D",  # principal
    "Finalizado plazo solicitudes":    "#264653",  # secundario
    "Actividad en desarrollo":         "#1a6b3c",  # verde
    "Publicadas Listas Provisionales": "#7b5ea7",  # violeta
    "Publicadas Listas Definitivas":   "#555",     # gris neutro
}


# ── Utilidades ────────────────────────────────────────────────────────────────

def slug(texto):
    texto = texto.lower()
    texto = re.sub(r"[áàä]", "a", texto)
    texto = re.sub(r"[éèë]", "e", texto)
    texto = re.sub(r"[íìï]", "i", texto)
    texto = re.sub(r"[óòö]", "o", texto)
    texto = re.sub(r"[úùü]", "u", texto)
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def fecha_rss(iso_str):
    dt = datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def nombre_cep(cep_str):
    """'18200016 - CEP Granada' → 'CEP Granada'"""
    if " - " in cep_str:
        return cep_str.split(" - ", 1)[1].strip()
    return cep_str


def provincia_de_cep(cep_str):
    """'18200016 - CEP Granada' → '18'"""
    codigo = cep_str.split(" - ")[0].strip()
    return codigo[:2]


# ── RSS ───────────────────────────────────────────────────────────────────────

def generar_xml_rss(titulo, descripcion, actividades, vistas):
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = titulo
    SubElement(channel, "link").text = CEP_URL
    SubElement(channel, "description").text = descripcion
    SubElement(channel, "language").text = "es"
    SubElement(channel, "lastBuildDate").text = fecha_rss(
        datetime.now(timezone.utc).isoformat()
    )

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
        SubElement(item, "link").text = a.get("URL") or CEP_URL
        SubElement(item, "guid", isPermaLink="false").text = codigo
        primera_vez = vistas.get(codigo, datetime.now(timezone.utc).isoformat())
        SubElement(item, "pubDate").text = fecha_rss(primera_vez)

    return minidom.parseString(tostring(rss, encoding="unicode")).toprettyxml(indent="  ")


def generar_rss(actividades, vistas):
    os.makedirs(RSS_DIR, exist_ok=True)

    # todas.xml
    with open(os.path.join(RSS_DIR, "todas.xml"), "w", encoding="utf-8") as f:
        f.write(generar_xml_rss(
            "CEP Radar",
            "Todas las actividades formativas de los CEP de Andalucía",
            actividades, vistas,
        ))

    # uno por CEP
    por_cep = defaultdict(list)
    for a in actividades:
        por_cep[a.get("CEP", "")].append(a)

    for cep, acts in sorted(por_cep.items()):
        nombre = nombre_cep(cep)
        fichero = slug(nombre) + ".xml"
        with open(os.path.join(RSS_DIR, fichero), "w", encoding="utf-8") as f:
            f.write(generar_xml_rss(
                f"Actividades {nombre}",
                f"Actividades formativas del {nombre}",
                acts, vistas,
            ))

    print(f"RSS: {1 + len(por_cep)} ficheros generados en {RSS_DIR}/")
    return por_cep


# ── HTML ──────────────────────────────────────────────────────────────────────

SVG_CEP = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
           'viewBox="0 0 36 36" style="vertical-align:-.2em;flex-shrink:0">'
           '<path fill="#ffcc4d" d="M36 34a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V15a2 2 0 0 1 2-2h32a2 2 0 0 1 2 2z"/>'
           '<path fill="#6d6e71" d="M34 13H2a2 2 0 0 0-2 2h36a2 2 0 0 0-2-2"/>'
           '<path fill="#3b88c3" d="M2 24h32v4H2zm0-6h32v4H2zm0 12h32v4H2z"/>'
           '<path fill="#ffcc4d" d="M28 17h2v18h-2z"/>'
           '<path fill="#ffe8b6" d="M22 0H6a2 2 0 0 0-2 2v34h20V2a2 2 0 0 0-2-2"/>'
           '<path fill="#808285" d="M22 0H6a2 2 0 0 0-2 2h20a2 2 0 0 0-2-2"/>'
           '<path fill="#55acee" d="M6 18h16v4H6zm0 6h16v4H6zm0 6h16v4H6z"/>'
           '<path fill="#ffe8b6" d="M10 7h2v29h-2zm6 0h2v29h-2z"/>'
           '<path fill="#269" d="M12 30h4v6h-4z"/>'
           '<circle cx="14" cy="9" r="6" fill="#a7a9ac"/>'
           '<circle cx="14" cy="9" r="4" fill="#e6e7e8"/>'
           '<path fill="#a0041e" d="M17 10h-3a1 1 0 0 1-1-1V4a1 1 0 0 1 2 0v4h2a1 1 0 1 0 0-2"/>'
           '</svg>')

SVG_MODAL = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
             'viewBox="0 0 36 36" style="vertical-align:-.2em;flex-shrink:0">'
             '<path fill="#553788" d="M15 31c0 2.209-.791 4-3 4H5c-4 0-4-14 0-14h7c2.209 0 3 1.791 3 4z"/>'
             '<path fill="#9266cc" d="M34 33h-1V23h1a1 1 0 1 0 0-2H10c-4 0-4 14 0 14h24a1 1 0 1 0 0-2"/>'
             '<path fill="#ccd6dd" d="M34.172 33H11c-2 0-2-10 0-10h23.172c1.104 0 1.104 10 0 10"/>'
             '<path fill="#99aab5" d="M11.5 25h23.35c-.135-1.175-.36-2-.678-2H11c-1.651 0-1.938 6.808-.863 9.188C9.745 29.229 10.199 25 11.5 25"/>'
             '<path fill="#269" d="M12 8a4 4 0 0 1-4 4H4C0 12 0 1 4 1h4a4 4 0 0 1 4 4z"/>'
             '<path fill="#55acee" d="M31 10h-1V3h1a1 1 0 1 0 0-2H7C3 1 3 12 7 12h24a1 1 0 1 0 0-2"/>'
             '<path fill="#ccd6dd" d="M31.172 10H8c-2 0-2-7 0-7h23.172c1.104 0 1.104 7 0 7"/>'
             '<path fill="#99aab5" d="M8 5h23.925c-.114-1.125-.364-2-.753-2H8C6.807 3 6.331 5.489 6.562 7.5C6.718 6.142 7.193 5 8 5"/>'
             '<path fill="#f4900c" d="M20 17a4 4 0 0 1-4 4H6c-4 0-4-9 0-9h10a4 4 0 0 1 4 4z"/>'
             '<path fill="#ffac33" d="M35 19h-1v-5h1a1 1 0 1 0 0-2H15c-4 0-4 9 0 9h20a1 1 0 1 0 0-2"/>'
             '<path fill="#ccd6dd" d="M35.172 19H16c-2 0-2-5 0-5h19.172c1.104 0 1.104 5 0 5"/>'
             '<path fill="#99aab5" d="M16 16h19.984c-.065-1.062-.334-2-.812-2H16c-1.274 0-1.733 2.027-1.383 3.5c.198-.839.657-1.5 1.383-1.5"/>'
             '</svg>')

SVG_DIRIGIDO = ('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" '
                'viewBox="0 0 20 20" style="vertical-align:-.25em;flex-shrink:0">'
                '<g fill="none">'
                '<path fill="url(#SVGDgDlbbOE-__SUFFIX__)" d="M16.75 8h-2.5C13.56 8 13 8.56 13 9.25v4.25a2.5 2.5 0 0 0 5 0V9.25C18 8.56 17.44 8 16.75 8"/>'
                '<path fill="url(#SVG3joIyeuT-__SUFFIX__)" fill-opacity="0.5" d="M16.75 8h-2.5C13.56 8 13 8.56 13 9.25v4.25a2.5 2.5 0 0 0 5 0V9.25C18 8.56 17.44 8 16.75 8"/>'
                '<path fill="#f00" fill-opacity="0.2" d="M5.75 8h-2.5C2.56 8 2 8.56 2 9.25v4.25a2.5 2.5 0 0 0 5 0V9.25C7 8.56 6.44 8 5.75 8"/>'
                '<path fill="url(#SVGS5bxybNu-__SUFFIX__)" d="M5.75 8h-2.5C2.56 8 2 8.56 2 9.25v4.25a2.5 2.5 0 0 0 5 0V9.25C7 8.56 6.44 8 5.75 8"/>'
                '<path fill="url(#SVGPMQZobgv-__SUFFIX__)" fill-opacity="0.5" d="M5.75 8h-2.5C2.56 8 2 8.56 2 9.25v4.25a2.5 2.5 0 0 0 5 0V9.25C7 8.56 6.44 8 5.75 8"/>'
                '<path fill="url(#SVGfDGJVc8A-__SUFFIX__)" d="M6 9.25C6 8.56 6.56 8 7.25 8h5.5c.69 0 1.25.56 1.25 1.25V14a4 4 0 0 1-8 0z"/>'
                '<path fill="url(#SVGit9mverY-__SUFFIX__)" d="M6 9.25C6 8.56 6.56 8 7.25 8h5.5c.69 0 1.25.56 1.25 1.25V14a4 4 0 0 1-8 0z"/>'
                '<path fill="url(#SVGG3GWrZ8i-__SUFFIX__)" d="M17.5 5a2 2 0 1 1-4 0a2 2 0 0 1 4 0m-2 2a2 2 0 1 0 0-4a2 2 0 0 0 0 4"/>'
                '<path fill="url(#SVGG3GWrZ8i-__SUFFIX__)" d="M17.5 5a2 2 0 1 1-4 0a2 2 0 0 1 4 0"/>'
                '<path fill="url(#SVG2UnaAcfE-__SUFFIX__)" d="M6.5 5a2 2 0 1 1-4 0a2 2 0 0 1 4 0m-2 2a2 2 0 1 0 0-4a2 2 0 0 0 0 4"/>'
                '<path fill="url(#SVG2UnaAcfE-__SUFFIX__)" d="M6.5 5a2 2 0 1 1-4 0a2 2 0 0 1 4 0"/>'
                '<path fill="url(#SVGtLiXNnrC-__SUFFIX__)" d="M12.5 4.5a2.5 2.5 0 1 1-5 0a2.5 2.5 0 0 1 5 0"/>'
                '<defs>'
                '<linearGradient id="SVGDgDlbbOE-__SUFFIX__" x1="14.189" x2="18.721" y1="9.063" y2="13.586" gradientUnits="userSpaceOnUse"><stop offset=".125" stop-color="#7a41dc"/><stop offset="1" stop-color="#5b2ab5"/></linearGradient>'
                '<linearGradient id="SVGS5bxybNu-__SUFFIX__" x1="3.189" x2="7.721" y1="9.063" y2="13.586" gradientUnits="userSpaceOnUse"><stop offset=".125" stop-color="#9c6cfe"/><stop offset="1" stop-color="#7a41dc"/></linearGradient>'
                '<linearGradient id="SVGfDGJVc8A-__SUFFIX__" x1="7.902" x2="13.402" y1="9.329" y2="16.354" gradientUnits="userSpaceOnUse"><stop offset=".125" stop-color="#bd96ff"/><stop offset="1" stop-color="#9c6cfe"/></linearGradient>'
                '<linearGradient id="SVGit9mverY-__SUFFIX__" x1="10" x2="18.372" y1="6.81" y2="19.324" gradientUnits="userSpaceOnUse"><stop stop-color="#885edb" stop-opacity="0"/><stop offset="1" stop-color="#e362f8"/></linearGradient>'
                '<linearGradient id="SVGG3GWrZ8i-__SUFFIX__" x1="14.451" x2="16.49" y1="3.532" y2="6.787" gradientUnits="userSpaceOnUse"><stop offset=".125" stop-color="#7a41dc"/><stop offset="1" stop-color="#5b2ab5"/></linearGradient>'
                '<linearGradient id="SVG2UnaAcfE-__SUFFIX__" x1="3.451" x2="5.49" y1="3.532" y2="6.787" gradientUnits="userSpaceOnUse"><stop offset=".125" stop-color="#9c6cfe"/><stop offset="1" stop-color="#7a41dc"/></linearGradient>'
                '<linearGradient id="SVGtLiXNnrC-__SUFFIX__" x1="8.689" x2="11.237" y1="2.665" y2="6.734" gradientUnits="userSpaceOnUse"><stop offset=".125" stop-color="#bd96ff"/><stop offset="1" stop-color="#9c6cfe"/></linearGradient>'
                '<radialGradient id="SVG3joIyeuT-__SUFFIX__" cx="0" cy="0" r="1" gradientTransform="matrix(4.02372 0 0 10.9215 12.214 11.813)" gradientUnits="userSpaceOnUse"><stop offset=".433" stop-color="#3b148a"/><stop offset="1" stop-color="#3b148a" stop-opacity="0"/></radialGradient>'
                '<radialGradient id="SVGPMQZobgv-__SUFFIX__" cx="0" cy="0" r="1" gradientTransform="matrix(-4.45292 0 0 -12.0865 8.62 11.813)" gradientUnits="userSpaceOnUse"><stop offset=".433" stop-color="#3b148a"/><stop offset="1" stop-color="#3b148a" stop-opacity="0"/></radialGradient>'
                '</defs></g></svg>')

SVG_ESTADO = ('<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" '
              'viewBox="0 0 48 48" style="vertical-align:-.45em;flex-shrink:0">'
              '<g fill="none">'
              '<path fill="url(#SVGKEGjcdgh)" d="M34.895 25.272a1.75 1.75 0 0 0-1.75 0l-6.255 3.611a1.75 1.75 0 0 0-.875 1.516v7.222c0 .625.333 1.203.875 1.516l6.255 3.611a1.75 1.75 0 0 0 1.75 0l6.255-3.611a1.75 1.75 0 0 0 .875-1.516V30.4a1.75 1.75 0 0 0-.875-1.516z"/>'
              '<path fill="url(#SVGDtRoAebw)" d="M14 26a8 8 0 1 0 0 16a8 8 0 0 0 0-16"/>'
              '<path fill="url(#SVGUziOxdHW)" d="M30.75 6A4.75 4.75 0 0 0 26 10.75v6.5A4.75 4.75 0 0 0 30.75 22h6.5A4.75 4.75 0 0 0 42 17.25v-6.5A4.75 4.75 0 0 0 37.25 6z"/>'
              '<path fill="url(#SVGpavGQe4Z)" d="M16.904 7.797C15.7 5.4 12.31 5.4 11.105 7.797l-4.743 9.432c-1.1 2.184.473 4.771 2.9 4.771h9.487c2.426 0 3.998-2.587 2.899-4.771z"/>'
              '<defs>'
              '<linearGradient id="SVGKEGjcdgh" x1="16.676" x2="38.743" y1="17.56" y2="40.033" gradientUnits="userSpaceOnUse"><stop stop-color="#52d17c"/><stop offset="1" stop-color="#22918b"/></linearGradient>'
              '<linearGradient id="SVGDtRoAebw" x1="6" x2="22" y1="26" y2="42" gradientUnits="userSpaceOnUse"><stop stop-color="#0fafff"/><stop offset="1" stop-color="#2764e7"/></linearGradient>'
              '<linearGradient id="SVGUziOxdHW" x1="19.333" x2="39" y1="-2" y2="23.5" gradientUnits="userSpaceOnUse"><stop stop-color="#ffcd0f"/><stop offset="1" stop-color="#fe8401"/></linearGradient>'
              '<linearGradient id="SVGpavGQe4Z" x1="6.576" x2="17.618" y1="9" y2="20.472" gradientUnits="userSpaceOnUse"><stop stop-color="#f24a9d"/><stop offset="1" stop-color="#d7257d"/></linearGradient>'
              '</defs></g></svg>')


def icono_dirigido(a):
    suffix = slug(a.get("Código") or a.get("Título") or a.get("Dirigido a") or "dirigido")
    return SVG_DIRIGIDO.replace("__SUFFIX__", suffix)


SVG_FECHAS = ('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" '
              'viewBox="0 0 28 28" style="vertical-align:-.25em;flex-shrink:0">'
              '<g fill="none">'
              '<path fill="url(#SVGtN4pBdhY-__SUFFIX__)" d="M25 21.75A3.25 3.25 0 0 1 21.75 25H6.25A3.25 3.25 0 0 1 3 21.75V9l11-1l11 1z"/>'
              '<path fill="url(#SVGlH4OEXcs-__SUFFIX__)" d="M25 21.75A3.25 3.25 0 0 1 21.75 25H6.25A3.25 3.25 0 0 1 3 21.75V9l11-1l11 1z"/>'
              '<g filter="url(#SVGqRFnndiJ-__SUFFIX__)">'
              '<path fill="url(#SVGd0M2kbKm-__SUFFIX__)" d="M8.749 17.502a1.25 1.25 0 1 1 0 2.5a1.25 1.25 0 0 1 0-2.5m5.254 0a1.25 1.25 0 1 1 0 2.5a1.25 1.25 0 0 1 0-2.5m-5.254-5a1.25 1.25 0 1 1 0 2.5a1.25 1.25 0 0 1 0-2.5m5.254 0a1.25 1.25 0 1 1 0 2.5a1.25 1.25 0 0 1 0-2.5m5.255 0a1.25 1.25 0 1 1 0 2.5a1.25 1.25 0 0 1 0-2.5"/>'
              '</g>'
              '<path fill="url(#SVGvu0mobrR-__SUFFIX__)" d="M21.75 3A3.25 3.25 0 0 1 25 6.25V9H3V6.25A3.25 3.25 0 0 1 6.25 3z"/>'
              '<defs>'
              '<linearGradient id="SVGtN4pBdhY-__SUFFIX__" x1="17.972" x2="11.828" y1="27.088" y2="8.803" gradientUnits="userSpaceOnUse"><stop stop-color="#b3e0ff"/><stop offset="1" stop-color="#b3e0ff"/></linearGradient>'
              '<linearGradient id="SVGlH4OEXcs-__SUFFIX__" x1="16.357" x2="19.402" y1="14.954" y2="28.885" gradientUnits="userSpaceOnUse"><stop stop-color="#dcf8ff" stop-opacity="0"/><stop offset="1" stop-color="#ff6ce8" stop-opacity="0.7"/></linearGradient>'
              '<linearGradient id="SVGd0M2kbKm-__SUFFIX__" x1="12.821" x2="15.099" y1="11.636" y2="26.649" gradientUnits="userSpaceOnUse"><stop stop-color="#0078d4"/><stop offset="1" stop-color="#0067bf"/></linearGradient>'
              '<linearGradient id="SVGvu0mobrR-__SUFFIX__" x1="3" x2="21.722" y1="3" y2="-3.157" gradientUnits="userSpaceOnUse"><stop stop-color="#0094f0"/><stop offset="1" stop-color="#2764e7"/></linearGradient>'
              '<filter id="SVGqRFnndiJ-__SUFFIX__" width="15.676" height="10.167" x="6.165" y="11.835" color-interpolation-filters="sRGB" filterUnits="userSpaceOnUse"><feFlood flood-opacity="0" result="BackgroundImageFix"/><feColorMatrix in="SourceAlpha" result="hardAlpha" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"/><feOffset dy=".667"/><feGaussianBlur stdDeviation=".667"/><feColorMatrix values="0 0 0 0 0.1242 0 0 0 0 0.323337 0 0 0 0 0.7958 0 0 0 0.32 0"/><feBlend in2="BackgroundImageFix" result="effect1_dropShadow_378174_9797"/><feBlend in="SourceGraphic" in2="effect1_dropShadow_378174_9797" result="shape"/></filter>'
              '</defs></g></svg>')


def icono_fechas(a):
    suffix = slug("fechas_" + (a.get("Código") or a.get("Título") or a.get("Inicio") or "actividad"))
    return SVG_FECHAS.replace("__SUFFIX__", suffix)


SVG_ENLACE = ('<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" '
              'viewBox="0 0 640 640" aria-hidden="true" focusable="false">'
              '<path fill="currentColor" d="M384 64c-17.7 0-32 14.3-32 32s14.3 32 32 32h82.7L265.3 329.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L512 173.3V256c0 17.7 14.3 32 32 32s32-14.3 32-32V96c0-17.7-14.3-32-32-32zm-240 96c-44.2 0-80 35.8-80 80v256c0 44.2 35.8 80 80 80h256c44.2 0 80-35.8 80-80v-80c0-17.7-14.3-32-32-32s-32 14.3-32 32v80c0 8.8-7.2 16-16 16H144c-8.8 0-16-7.2-16-16V240c0-8.8 7.2-16 16-16h80c17.7 0 32-14.3 32-32s-14.3-32-32-32z"/>'
              '</svg>')

SVG_RSS = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
           'viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
           '<path fill="currentColor" d="M6.18 17.82a2.18 2.18 0 1 1-4.36 0a2.18 2.18 0 0 1 4.36 0M2 9.5v3.1a9.4 9.4 0 0 1 9.4 9.4h3.1C14.5 15.1 8.9 9.5 2 9.5M2 2v3.1c9.33 0 16.9 7.57 16.9 16.9H22C22 10.95 13.05 2 2 2"/>'
           '</svg>')

SVG_AVATAR = ('<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" '
              'viewBox="0 0 117.96 117.96" aria-hidden="true" focusable="false" '
              'style="shape-rendering:geometricPrecision;text-rendering:geometricPrecision;'
              'image-rendering:optimizeQuality;fill-rule:evenodd;clip-rule:evenodd">'
              '<circle cx="58.98" cy="58.98" r="58.98" style="fill:#fff"/>'
              '<g>'
              '<path d="M57.29 71.03h4.46c1.25 0 2.62.34 2.62 1.57 0 .68-1.47.91-2.1 1.05 0 1.3-.46 3.32.44 4.95l1.61 2.06c1.33 1.7 3.9 4.42 4.96 5.79 1 1.29 4.28 4.54 4.28 6.62 0 1.84-.33 2.67-2.1 3.55-2.66 1.31-9.61.65-12.6.65l-8.66.13c-2.67 0-5.64-.91-5.64-3.54 0-2.44.71-3.16 2.39-5.22 1.05-1.29 2.04-2.45 3.08-3.75.54-.67 1.01-1.18 1.54-1.87 1.06-1.35 4.14-4.39 4.14-6.09l-.13-3.28c-.64-.15-1.57-.51-2.1-.78.47-.98-.35-1.84 3.81-1.84zm21.38 2.23c-4.4 0-5.99-1.84-9.79-4.11-.37-.22-.64-.37-.99-.59-2.76-1.74-5.65-2.78-9.16-2.78-5.5 0-9.8 3.89-13.69 5.86-1.7.87-2.8 1.62-5.2 1.62-3.6 0-5.94-3.26-6.87-6.25-.58-1.84-1.22-6.05-1.65-8.19-.2-1.04-.44-1.8-.66-2.75-.46.34-1 1.75-1.23 2.45-.17.5-.34.95-.45 1.38-2.1 7.75-1.1 16.91 2.03 24.16 1.69 3.91 3.96 7.37 6.36 10.57 1.82 2.43 1.86 2 2.96 3.33.19.23.24.38.46.58.24.22.32.22.59.46l2.23 1.97c.82.68 1.65 1.23 2.53 1.81.79.53 1.75 1.08 2.66 1.53 12.28 6.1 24.01.27 31.97-9.93 1.16-1.47 2.61-3.38 3.54-4.99 3.3-5.74 5.78-13.06 5.78-19.94 0-3.62.04-5.07-.89-8.68-.41-1.57-.85-3.88-2.26-4.83-.25 3.05-1.01 8.09-1.92 10.81-.94 2.8-2.89 6.51-6.35 6.51z" style="fill:#254552"/>'
              '<path d="M38.92 23.54c-.78-.21-1.8-1.29-2.28-1.92a9.28 9.28 0 0 0-2.18-2.02c0 3.32.79 5.01.79 6.69-2.22.52-4.15 1.56-5.29 3.5-1.32 2.23-1.43 3.88-1.87 6.92-.27 1.85-.12 6.43.15 8.27.2 1.4.77 6.43 1.76 7.16.48-.9.55-2.69.77-3.82.6-3 1.06-2.94 3.62-3.34 1.02-.16 1.11-.03 1.44-.92 1.11-2.95 3.05-7.59 5.6-9.62.66-.52 1.34-1.04 2.2-1.35 5.42-1.92 11.37.28 16.89 1.65 1.09.27 1.94.55 3.07.74 5.77.95 12.28-.11 15.64 3.37.56.57 1.09 1.56 1.5 2.31l1.31 2.49c.65 1.32.77 1.13 2.33 1.48 3.37.76 2.49 2.96 3.3 6.14.14.56.21 1.12.58 1.39.1-.43.29-.75.44-1.26.67-2.26.71-4.09.74-6.35.01-.74.14-.92.14-1.7l-.19-3.36c-.31-2.16-.85-3.83-1.65-5.43L85.1 30.1c.34-1.47 4.33-6.11 4.33-10.37 0-.88-.37-2.83-.65-3.41-.73.35-5.36 1.97-6.43 1.97-3.21 0-4.59-.46-7.5-1.43-8.8-2.91-14.31-7.01-24.67-5.28-1.85.31-4.24 1.34-5.51 2.23-2.32 1.63-4.12 3.74-5.03 6.51-.27.81-.72 2.27-.72 3.22z" style="fill:#254652"/>'
              '<path d="M72.11 63.16c-4.31 0-8.39-3.44-8.39-7.48 0-3 .21-4.64 2.52-6.92 4.66-4.61 14.4-1.86 14.4 6 0 2.17-.77 3.83-1.98 5.36-.72.91-1.9 1.83-2.98 2.27-.92.38-2.23.77-3.57.77zm-25.58 0c-1.94 0-2.7.04-4.51-.87-6.53-3.33-6.87-15.79 4.64-15.79 1.14 0 2.37.42 3.15.78.6.28 1.91 1.24 2.31 1.76 2.08 2.69 2.96 5.77 1.63 9.13-1.12 2.85-4.27 4.99-7.22 4.99zM33.02 49.25c0 3.26 1.33 1.62 2 5.73.46 2.78.73 5.64 3.13 7.64.72.6 1.16 1.11 2.04 1.63 3.06 1.81 6.51 2.23 9.92.78 3.44-1.45 6.79-5.11 6.79-9.09 0-2.01-.27-3.5-.27-4.98 1.58-.13 1.69-.64 3.66-.25.5.1.61.23 1.2.25 0 4.41-1.66 7.55 3.18 12.03 5.29 4.91 14.7 3.65 17.43-3.88.55-1.51 1.08-5.62 1.67-6.47.69-1.02 1.09-1.2 1.24-2.82.37-3.76-3.09-1.89-5-3.09-1.3-.81-4.04-2.24-5.53-2.6-2.24-.54-4.72-.39-6.9.58-3.29 1.47-2.41 3.2-7.25 2.68-2.34-.24-4.76.22-5.89-.28l-2.75-1.58c-8.07-4.41-12.13.96-14.29 1.54-2.31.63-4.38-.64-4.38 2.18zM54.66 90.18c.14.52.7.63 1.42.95.33.15.16.13.55.23-.04.56-.15.44-.26.92-.89-.02-1.4-.45-1.97-.78-.87-.49-1.18-.33-1.18-1.71.49-.11.96-.5 1.49-.74.79-.37 1.09-.57 1.79-.57 0 .9.06.88-.76 1.2-.41.16-.71.41-1.08.5zm7.22-1.83c.57.04 3.02 1.15 3.02 2.1 0 .57-3.59 2.6-3.34 1.24.13-.71 1.66-.63 1.9-1.51-.54-.14-1.51-.87-1.97-1.18.15-.29.22-.39.39-.65zm-3.54 5.9c-1.76 0-.68-1.03.28-3.92l.97-2.57c.49-1.2 1.11-.31 1.11-.07 0 .68-2.13 5.55-2.36 6.56zm-11.81-.52c0 1.19 1.56 1.44 2.64 1.55 1.97.21 11.21.23 12.71.15 1.98-.1.48-.21 2.89-.01 1.21.1 4.15-.05 5.11-.26 3.11-.67 1.31-3.44.04-4.88l-1.42-1.6c-1.61-2.05-1.99-2.32-3.47-4.53-.37.18-.89.19-1.39.32-.5.12-.94.26-1.41.42-3.65 1.2-5.08-.83-8.75-1.13-1.39 2.07-6.95 7.67-6.95 9.97z" style="fill:#299c8e"/>'
              '<path d="M40.23 54.1c0 .88-.15 1.55.68 1.23.36-.14.4-.31.55-.66.47-1.15.92-2.15 1.76-3.09.15-.17 1.99-1.8.56-1.8-1.71 0-3.55 2.44-3.55 4.32zM66.47 54.24c1.18-.28 1.38-1.79 1.97-2.75.56-.92 1.56-1.71 1.84-2.9-1.44 0-2.15.34-3.17 1.82-.98 1.42-.96 2.46-.64 3.83z" style="fill:#299c8e"/>'
              '</g>'
              '</svg>')

SVG_LOGO = ('<svg class="site-logo" xmlns="http://www.w3.org/2000/svg" xml:space="preserve" '
            'viewBox="0 0 8.16 8.16" aria-hidden="true" focusable="false" '
            'style="shape-rendering:geometricPrecision;text-rendering:geometricPrecision;'
            'image-rendering:optimizeQuality;fill-rule:evenodd;clip-rule:evenodd">'
            '<defs><style>.fil0{fill:#2a9d8f}.fil1{fill:#2b2a29}</style></defs>'
            '<g>'
            '<circle cx="4.08" cy="4.08" r="4.08" fill="#fff"/>'
            '<path d="m2.53 6.28-.52.06c-.05.09-.24 1.01-.28 1.19.07 0 .43-.05.73-.04.24.01.45.05.66.11.62.17.87.51 1 .56.48-.5 1.28-.71 1.97-.66.11.01.25.04.35.03l-.27-1.16c-.03-.02 0-.01-.06-.02l-.17-.03c-.08-.01-.16-.03-.24-.04.08-.06.21-.1.27-.15.06-.05.1-.18-.08-.26-.21-.1-.39-.19-.59-.28-.17-.08-1.11-.55-1.22-.54-.08.01-1.63.73-1.8.82-.09.05-.17.18-.05.26.09.07.22.09.3.15zm2.52.46v-.25c-.24.1-.84.43-.95.42-.15 0-.72-.37-.96-.42 0 .41-.07.48.27.64.2.09.45.19.6.31.11.09.19 0 .29-.06.22-.14.43-.21.61-.31.12-.08.14-.13.14-.33zm-2.47-.71.66.32c.23.11.46.21.68.33.24.13.21.09.7-.15.14-.07.57-.29.69-.33v.25c0 .19-.02.13-.04.21l-.03.46c.11.05.18.05.27-.02 0-.04-.03-.43-.04-.47-.05-.17-.04-.28-.03-.48l.2-.12c-.07-.06-1.45-.72-1.53-.73-.05 0-.68.3-.77.34l-.76.39z" class="fil0"/>'
            '<path d="M5.98.83c.16.05.29.17.4.25.07.05.11.1.18.15.26.22.58.55.74.87.19.24.43.92.49 1.3.21 1.29-.16 2.43-1.03 3.33-.26.27-.27.22-.23.38.01.07.03.13.05.19.22-.11.68-.66.8-.82.21-.31.41-.66.55-1.07.46-1.28.23-2.78-.59-3.83-.21-.26-.35-.41-.59-.62C5.28-.31 3.18-.27 1.64.8c-.08.06-.15.11-.22.18-.27.25-.33.27-.6.62-.23.3-.42.65-.57 1.05-.47 1.23-.27 2.77.55 3.83.05.08.11.14.17.22.11.15.48.51.63.59.03-.2.11-.26.04-.34-.32-.34-.31-.24-.65-.72-.22-.3-.46-.83-.57-1.26-.27-1.13-.01-2.1.49-2.93.22-.37.53-.67.87-.93.96-.76 2.39-1 3.58-.58.15.05.55.22.62.3z" class="fil1"/>'
            '<path d="M5.46 1.77c-.01.03-.01.05-.03.07-.04.05.01.02-.05.03 0 .1-.19.38-.24.47-.05.09-.21.41-.26.45-.02.07-.03.09-.08.11-.02.12-.18.36-.24.47-.05.09-.21.39-.27.44l.12.09c.05.03.07.07.12.12 0-.01.01-.01.01-.01l.08-.07c.17-.11.66-.47.77-.5.01-.04 0-.03.04-.06.03-.01.04-.01.07-.01 0-.07.11-.11.17-.15.12-.09.56-.42.67-.43 0-.05.05-.09.11-.08.03-.08.12-.12.19-.16.08-.06.15-.11.22-.16.13-.09.3-.22.44-.29-.16-.32-.48-.65-.74-.87-.07-.05-.11-.1-.18-.15-.11-.08-.24-.2-.4-.25-.04.1-.06.14-.12.24-.04.08-.09.15-.13.24-.09.17-.19.31-.27.46z" class="fil0"/>'
            '<path d="M4.53 4.02c-.05-.05-.07-.09-.12-.12l-.12-.09c-.11-.01-.41-.11-.59.19-.31.49.33.93.69.63.31-.25.15-.53.14-.61z" class="fil1"/>'
            '<path d="M4.8 2.9c.05-.02.06-.04.08-.11-.2-.06-.31-.13-.54-.17-1.31-.19-2.3 1.17-1.73 2.32.06.13.22.36.31.41l.1-.04c-.05-.1-.14-.13-.28-.39-.07-.15-.13-.33-.16-.51-.12-.89.66-1.76 1.69-1.67.25.03.33.09.53.16zM2.22 2.32a.196.196 0 0 0-.09-.09c-.46.48-.76 1.02-.83 1.75-.03.39.03.78.16 1.12.05.14.33.71.49.81L2 5.82c-.06-.16-.25-.29-.43-.79-.12-.32-.17-.69-.13-1.06.03-.36.13-.67.27-.95.17-.33.28-.44.51-.7zM6.34 2.79c.15.27.21.33.31.67.21.7.1 1.42-.25 2.04-.06.11-.15.2-.21.3.02.05.04.09.06.12.07-.06.16-.21.22-.3.07-.1.13-.22.19-.34.27-.57.28-1.23.12-1.82-.12-.43-.23-.5-.33-.75-.06-.01-.11.03-.11.08zM2.6 1.85c.02.06.03.09.08.11.21-.09.23-.14.58-.26.21-.07.47-.12.71-.13.27-.01.54.01.78.07.41.1.41.16.63.23.06-.01.01.02.05-.03.02-.02.02-.04.03-.07-.51-.17-.75-.36-1.47-.33-.28.02-.5.06-.75.14-.37.11-.42.18-.64.27zM5.39 3.44c.12.32.28.51.21 1.02-.07.49-.33.68-.43.84l.1.05c.33-.21.56-.95.43-1.51-.06-.21-.13-.31-.2-.47-.03 0-.04 0-.07.01-.04.03-.03.02-.04.06z" class="fil1"/>'
            '<path d="M2.13 2.23c.05.03.06.04.09.09.13.03.24.06.35-.02.13-.09.08-.17.11-.34-.05-.02-.06-.05-.08-.11-.14-.01-.21-.13-.39 0-.15.11-.1.2-.08.38z" class="fil0"/>'
            '</g>'
            '</svg>')


def badge(estado):
    color = BADGE_COLOR.get(estado, "#555")
    return f'<span class="badge" style="background:{color}">{estado}</span>'


def card_html(a):
    estado = a.get("Estado", "")
    url = a.get("URL", "")
    enlace = (f'<a class="card-link" href="{url}" target="_blank" rel="noopener">'
              f'Ver actividad {SVG_ENLACE}</a>') if url else ""
    return f"""
    <div class="card"
         data-cep="{slug(nombre_cep(a.get('CEP','')))}"
         data-modalidad="{slug(a.get('Modalidad',''))}"
         data-estado="{slug(a.get('Estado',''))}"
         data-dirigido="{slug(a.get('Dirigido a',''))}">
      <div class="card-header">
        <span class="codigo">{a.get('Código','')}</span>
        {badge(estado)}
      </div>
      <h3>{a.get('Título','')}</h3>
      <div class="meta">
        <span>{SVG_CEP} {a.get('CEP','')}</span>
        <span>{SVG_MODAL} {a.get('Modalidad','')}</span>
        <span>{icono_dirigido(a)} {a.get('Dirigido a','')}</span>
        <span>{icono_fechas(a)} {a.get('Inicio','')} → {a.get('Fin','')}</span>
      </div>
      {enlace}
    </div>"""


def panel_filtros_html(por_cep, actividades):
    # CEPs agrupados por provincia
    por_provincia = defaultdict(list)
    for cep in sorted(por_cep.keys()):
        por_provincia[provincia_de_cep(cep)].append(cep)

    cep_cols = ""
    for prov in sorted(por_provincia, key=lambda p: PROVINCIA_NOMBRE.get(p, p)):
        nombre_prov = PROVINCIA_NOMBRE.get(prov, prov)
        items = "".join(
            f'<label><input type="checkbox" class="f-cep" value="{slug(nombre_cep(c))}"'
            f' onchange="filtrar()"><span class="cep-txt">{nombre_cep(c)}'
            f' <small>({len(por_cep[c])})</small></span></label>'
            for c in por_provincia[prov]
        )
        cep_cols += f'<div class="prov-col"><strong>{nombre_prov}</strong>{items}</div>'

    # Modalidades, estados y destinatarios únicos presentes en los datos
    modalidades = sorted({a.get("Modalidad", "")   for a in actividades if a.get("Modalidad")})
    estados     = sorted({a.get("Estado", "")      for a in actividades if a.get("Estado")})
    dirigidos   = sorted({a.get("Dirigido a", "")  for a in actividades if a.get("Dirigido a")})

    modal_items   = "".join(
        f'<label><input type="checkbox" class="f-modal" value="{slug(m)}" onchange="filtrar()"> {m}</label>'
        for m in modalidades
    )
    estado_items  = "".join(
        f'<label><input type="checkbox" class="f-estado" value="{slug(e)}" onchange="filtrar()"> {e}</label>'
        for e in estados
    )
    dirigido_items = "".join(
        f'<label><input type="checkbox" class="f-dirigido" value="{slug(d)}" onchange="filtrar()"> {d}</label>'
        for d in dirigidos
    )

    return f"""
  <div id="panel-filtros" class="panel-filtros hidden">
    <details class="filter-section">
      <summary>{SVG_CEP} Centros de Educación del Profesorado, CEP's</summary>
      <div class="cep-grid">{cep_cols}</div>
    </details>
    <details class="filter-section">
      <summary>{SVG_MODAL} Modalidad</summary>
      <div class="opciones-row">{modal_items}</div>
    </details>
    <details class="filter-section">
      <summary>{SVG_DIRIGIDO} Dirigido a</summary>
      <div class="opciones-row">{dirigido_items}</div>
    </details>
    <details class="filter-section">
      <summary>{SVG_ESTADO} Estado</summary>
      <div class="opciones-row">{estado_items}</div>
    </details>
  </div>"""


def panel_rss_html(por_cep):
    por_provincia = defaultdict(list)
    for cep in sorted(por_cep.keys()):
        por_provincia[provincia_de_cep(cep)].append(cep)

    rss_cols = ""
    for prov in sorted(por_provincia, key=lambda p: PROVINCIA_NOMBRE.get(p, p)):
        nombre_prov = PROVINCIA_NOMBRE.get(prov, prov)
        items = "".join(
            f'<button onclick="copiarRSS(\'rss/{slug(nombre_cep(c))}.xml\')">'
            f'<span>{nombre_cep(c)}</span>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" style="flex-shrink:0;opacity:.45"><path fill="currentColor" d="M15.24 2h-3.894c-1.764 0-3.162 0-4.255.148c-1.126.152-2.037.472-2.755 1.193c-.719.721-1.038 1.636-1.189 2.766C3 7.205 3 8.608 3 10.379v5.838c0 1.548.92 2.88 2.227 3.493C5.101 20.5 5 20.102 5 19.614v-9.019c0-1.428 0-2.557.1-3.448c.105-.921.33-1.748.81-2.498c-.398 0-.76.013-1.102.05c.047-.276.108-.537.19-.784h.001c.47-1.39 1.503-2.21 2.984-2.528C8.868 1.148 10.292 1 12 1h3.24c1.187 0 2.14.948 2.14 2.119v.36a4.4 4.4 0 0 1 1-.411V3.12C18.38 1.396 16.975 0 15.24 0z"/><path fill="currentColor" d="M11.039 5h5.76c.652 0 1.201.52 1.201 1.163v13.674c0 .643-.549 1.163-1.201 1.163h-5.76c-.652 0-1.201-.52-1.201-1.163V6.163C9.838 5.52 10.387 5 11.039 5"/></svg>'
            f'</button>'
            for c in por_provincia[prov]
        )
        rss_cols += f'<div class="rss-prov-col"><strong>{nombre_prov}</strong>{items}</div>'

    return f"""
  <div id="panel-rss" class="panel-rss hidden">
    <div class="rss-section">
      <h4>{SVG_RSS} ¿Qué es RSS?</h4>
      <div class="rss-intro">
        <p>RSS es un sistema de suscripción: en lugar de volver a revisar esta web cada día, <strong>tu lector RSS te avisa automáticamente</strong> cuando aparezcan actividades nuevas.</p>
        <p>Puedes usar lectores gratuitos como <strong>Feedly</strong>, <strong>Inoreader</strong> o la extensión <strong>RSS Feed Reader</strong> para Chrome y Firefox. Pulsa el enlace del feed que te interese y pégalo en tu lector.</p>
      </div>
    </div>
    <div class="rss-section">
      <h4>Feeds</h4>
      <p class="rss-feeds-desc">Pulsa sobre el botón <button class="rss-cep-btn" onclick="copiarRSS('rss/todas.xml')"><span>Suscribirse a todos los CEP's</span></button> para recibir información de todas las actividades, o bien selecciona el/los CEP's que desees a continuación:</p>
      <div class="rss-grid">{rss_cols}</div>
    </div>
  </div>"""


def generar_html(actividades, por_cep, generado):
    cards = "\n".join(card_html(a) for a in actividades)
    panel = panel_filtros_html(por_cep, actividades)
    rss_panel = panel_rss_html(por_cep)
    dt    = (datetime.fromisoformat(generado)
             .replace(tzinfo=timezone.utc)
             .astimezone(ZoneInfo("Europe/Madrid"))
             .strftime("%d/%m/%Y %H:%M"))
    total = len(actividades)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CEP Radar</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Domine:wght@400..700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --imperial-blue: #15616D;
      --blue-bell:     #264653;
      --ghost-white:   #FFFFFF;
      --magenta-bloom: #E76F51;
      --text:          #333333;
      --text-muted:    #6b7c80;
      --border:        #cfdee0;
      --bg:            #eef4f4;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: "Domine", Georgia, serif; background: var(--bg); color: var(--text); }}
    input, button {{ font: inherit; }}

    .sticky-top {{
      position: sticky;
      top: 0;
      z-index: 30;
    }}
    header {{
      background: var(--imperial-blue);
      color: var(--ghost-white);
      padding: 1.5rem 2rem 1rem;
      border-bottom: 4px solid var(--magenta-bloom);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 1rem 1.5rem;
      position: relative;
      z-index: 20;
    }}
    .header-tagline {{
      flex: 0 0 100%;
      font-size: .82rem;
      opacity: .7;
      padding-bottom: .4rem;
      border-top: 1px solid rgba(255,255,255,.12);
      padding-top: .65rem;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: .8rem;
    }}
    .site-logo {{
      width: 44px;
      height: 44px;
      flex-shrink: 0;
    }}
    header h1 {{ font-size: 1.4rem; letter-spacing: .01em; }}
    header p {{ font-size: .85rem; opacity: .75; margin-top: .25rem; }}
    .dev-credit {{
      display: flex; flex-direction: row; align-items: center; gap: .6rem;
      text-decoration: none; color: var(--ghost-white);
      opacity: .85; transition: opacity .15s;
      flex-shrink: 0;
    }}
    .dev-credit:hover {{ opacity: 1; }}
    .dev-credit-text {{
      display: flex; flex-direction: column; align-items: flex-end; gap: .15rem;
    }}
    .dev-credit-label {{
      font-size: .6rem; text-transform: uppercase;
      letter-spacing: .1em; opacity: .7; white-space: nowrap;
    }}
    .dev-credit-name {{
      font-size: .78rem; font-weight: 700; white-space: nowrap;
    }}
    .dev-credit-url {{
      font-size: .65rem; opacity: .7; white-space: nowrap;
    }}
    .dev-credit svg {{ width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0; }}
    .toolbar {{
      background: var(--ghost-white);
      padding: .85rem 2rem;
      display: flex; align-items: center; justify-content: space-between; gap: .75rem;
      border-bottom: 1px solid var(--border);
      box-shadow: 0 1px 4px rgba(10,36,99,.06);
      position: relative;
    }}
    .toolbar-left {{
      display: flex; align-items: center; gap: .75rem;
      flex: 0 0 50%; min-width: 0;
    }}
    .search-wrap {{
      flex: 1; min-width: 0;
      position: relative; display: flex; align-items: center;
    }}
    .search-wrap svg {{
      position: absolute; left: .6rem;
      color: var(--text-muted); pointer-events: none; flex-shrink: 0;
    }}
    .toolbar input {{
      width: 100%;
      padding: .45rem .75rem .45rem 2.1rem;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: .93rem;
      color: var(--text);
      background: white;
      outline-color: var(--blue-bell);
    }}
    .btn-filtrar, .btn-rss {{
      padding: .45rem 1rem;
      background: var(--imperial-blue);
      color: white;
      border: none; border-radius: 6px;
      font-size: .9rem; cursor: pointer;
      display: flex; align-items: center; gap: .35rem;
      transition: background .15s;
      white-space: nowrap;
    }}
    .btn-filtrar svg, .btn-rss svg {{ flex-shrink: 0; }}
    .btn-filtrar:hover, .btn-rss:hover {{ background: var(--blue-bell); }}
    .btn-filtrar.activo, .btn-rss.activo {{ background: var(--magenta-bloom); }}
    .panel-filtros {{
      position: absolute;
      top: 100%;
      left: 0; right: 0;
      z-index: 30;
      max-height: min(70vh, 600px);
      overflow: auto;
      background: white;
      border: 1px solid var(--border);
      border-radius: 0 0 8px 8px;
      padding: 1.25rem 2rem;
      box-shadow: 0 18px 45px rgba(10,36,99,.24);
    }}
    .panel-filtros.hidden, .panel-rss.hidden {{ display: none; }}
    .panel-filtros section {{ margin-bottom: 1.1rem; }}
    .panel-filtros section:last-child {{ margin-bottom: 0; }}
    .panel-filtros h4, .filter-section > summary {{
      font-size: .75rem; text-transform: uppercase;
      letter-spacing: .08em; color: var(--text-muted);
      margin-bottom: .6rem; padding-bottom: .3rem;
      border-bottom: 1px solid var(--border);
    }}
    .filter-section {{ margin-bottom: 1.1rem; }}
    .filter-section:last-child {{ margin-bottom: 0; }}
    .filter-section > summary {{
      list-style: none; cursor: default; display: flex; align-items: center; gap: .4rem;
    }}
    .filter-section > summary::marker,
    .filter-section > summary::-webkit-details-marker {{ display: none; }}
    @media (min-width: 641px) {{
      .filter-section > :not(summary) {{ display: block !important; }}
      .filter-section > .cep-grid,
      .filter-section > .rss-grid {{ display: grid !important; }}
      .filter-section > .opciones-row {{ display: flex !important; }}
      .filter-section > .rss-primary {{ display: inline-flex !important; }}
      .filter-section > summary {{ pointer-events: none; }}
    }}
    .cep-grid {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: .5rem 1rem; overflow-x: auto; }}
    .prov-col {{
      display: flex; flex-direction: column; gap: .3rem; min-width: 0;
    }}
    .prov-col strong {{
      font-size: .72rem; text-transform: uppercase;
      letter-spacing: .06em; color: var(--imperial-blue);
      margin-bottom: .15rem;
    }}
    .prov-col label {{
      display: flex; align-items: center; gap: .4rem;
      font-size: .75rem; cursor: pointer; color: var(--text); overflow: hidden;
    }}
    .cep-txt {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }}
    .opciones-row label {{
      display: flex; align-items: center; gap: .4rem;
      font-size: .75rem; cursor: pointer; color: var(--text);
    }}
    .prov-col label:hover, .opciones-row label:hover {{ color: var(--blue-bell); }}
    .prov-col small {{ color: var(--text-muted); font-size: .75rem; }}
    .opciones-row {{ display: flex; flex-wrap: wrap; gap: .4rem 1.5rem; }}
    .panel-filtros input[type="checkbox"] {{
      accent-color: var(--blue-bell); width: 14px; height: 14px; cursor: pointer;
    }}
    .panel-rss {{
      position: absolute;
      top: 100%;
      right: 2rem;
      z-index: 30;
      width: min(900px, calc(100vw - 4rem));
      max-height: min(70vh, 560px);
      overflow: auto;
      background: white;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
      box-shadow: 0 18px 45px rgba(10,36,99,.24);
    }}
    .rss-section {{ margin-bottom: 1.1rem; }}
    .rss-section:last-child {{ margin-bottom: 0; }}
    .rss-section h4 {{
      font-size: .75rem; text-transform: uppercase;
      letter-spacing: .08em; color: var(--text-muted);
      margin-bottom: .6rem; padding-bottom: .3rem;
      border-bottom: 1px solid var(--border);
    }}
    .rss-intro {{ padding-top: .5rem; }}
    .rss-intro p {{
      font-size: .8rem; color: var(--text-muted); line-height: 1.55;
      margin-bottom: .4rem;
    }}
    .rss-intro p:last-child {{ margin-bottom: 0; }}
    .rss-intro strong {{ color: var(--text); }}
    .rss-feeds-desc {{
      font-size: .8rem; color: var(--text-muted); line-height: 1.55;
      margin-bottom: 1rem;
    }}
    .rss-cep-btn {{
      display: inline-flex; align-items: center;
      background: var(--bg); border: none; cursor: pointer; font: inherit;
      color: var(--imperial-blue); font-size: .8rem; font-weight: 700;
      padding: .1rem .4rem; border-radius: 4px;
      transition: background .15s, transform .15s;
      vertical-align: baseline;
    }}
    .rss-grid {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: .5rem 1rem; overflow-x: auto; }}
    .rss-prov-col {{ display: flex; flex-direction: column; gap: .3rem; min-width: 0; }}
    .rss-prov-col strong {{
      font-size: .72rem; text-transform: uppercase;
      letter-spacing: .06em; color: var(--imperial-blue);
      margin-bottom: .15rem;
    }}
    .rss-prov-col button {{
      display: flex; align-items: center; gap: .5rem;
      background: none; border: none; cursor: pointer; font: inherit;
      color: var(--text); font-size: .75rem; padding: .15rem .3rem;
      overflow: hidden; text-align: left; border-radius: 4px;
      transition: background .15s, transform .15s;
    }}
    .rss-prov-col button span {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }}
    .rss-prov-col button svg {{ display: none; }}
    .rss-prov-col button:hover, .rss-cep-btn:hover {{
      background: var(--bg); color: var(--imperial-blue);
      transform: scale(1.04);
    }}
    @media (max-width: 640px) {{
      .rss-prov-col button:hover, .rss-cep-btn:hover {{ transform: none; }}
    }}
    #toast {{
      position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%);
      background: var(--blue-bell); color: #fff;
      padding: .65rem 1.25rem; border-radius: 8px;
      font-size: .85rem; box-shadow: 0 4px 16px rgba(0,0,0,.2);
      opacity: 0; pointer-events: none;
      transition: opacity .25s;
      z-index: 100; white-space: nowrap;
    }}
    #toast.visible {{ opacity: 1; }}

    main {{ padding: 1.5rem 2rem; max-width: 1140px; margin: 0 auto; }}
    .results-summary {{
      font-size: .86rem;
      color: var(--text-muted);
      margin-bottom: .8rem;
      font-variant-numeric: tabular-nums;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1rem;
    }}
    .card {{
      background: var(--ghost-white);
      border-radius: 10px;
      padding: 1rem 1.1rem;
      box-shadow: 0 1px 4px rgba(10,36,99,.08);
      border-left: 3px solid var(--blue-bell);
      display: flex;
      flex-direction: column;
      transition: box-shadow .15s, transform .15s;
    }}
    .card:hover {{
      box-shadow: 0 4px 14px rgba(10,36,99,.13);
      transform: translateY(-2px);
      border-left-color: var(--magenta-bloom);
    }}
    .card-header {{
      display: flex; justify-content: space-between;
      align-items: center; margin-bottom: .5rem;
    }}
    .codigo {{
      font-size: .75rem; color: var(--text-muted);
      font-family: monospace; letter-spacing: .03em;
    }}
    .badge {{
      color: white; font-size: .72rem;
      padding: .2rem .6rem; border-radius: 20px; white-space: nowrap;
    }}
    .card h3 {{
      font-size: .93rem; margin-bottom: .65rem; line-height: 1.45;
      color: var(--imperial-blue);
    }}
    .card-link {{
      align-self: flex-end;
      display: inline-flex; align-items: center; gap: .35rem;
      margin-top: auto;
      padding-top: .75rem;
      font-size: .82rem; font-weight: 600;
      color: var(--blue-bell); text-decoration: none;
      transition: color .15s;
    }}
    .card-link svg {{ flex-shrink: 0; }}
    .card-link:hover {{ color: var(--magenta-bloom); }}
    .meta {{
      display: flex; flex-direction: column; gap: .22rem;
      font-size: .81rem; color: var(--text-muted);
    }}
    .hidden {{ display: none; }}
    #sin-resultados {{
      text-align: center; padding: 3rem; color: var(--text-muted);
      display: none; grid-column: 1/-1;
    }}
    @media (max-width: 640px) {{
      header {{ padding: .6rem 1rem; gap: .4rem .75rem; align-items: flex-start; }}
      .brand {{ flex: 1; min-width: 0; gap: .5rem; align-items: flex-start; }}
      .site-logo {{ width: 28px; height: 28px; flex-shrink: 0; }}
      header h1 {{ font-size: .95rem; }}
      header p {{ font-size: .68rem; margin-top: .1rem; }}
      .dev-credit-text {{ display: none; }}
      .dev-credit svg {{ width: 28px; height: 28px; }}
      .header-tagline {{ font-size: .58rem; padding-top: .4rem; }}
      .toolbar {{ padding: .6rem 1rem; gap: .5rem; }}
      .toolbar-left {{ flex: 1; min-width: 0; }}
      .btn-txt {{ display: none; }}
      .btn-filtrar, .btn-rss {{ padding: .45rem .7rem; }}
      .toolbar input {{ font-size: .8rem; }}
      .panel-filtros {{ padding: .9rem 1rem; left: 0; right: 0; border-radius: 0; }}
      .cep-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .rss-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .opciones-row {{ gap: .3rem 1rem; }}
      .filter-section > summary {{
        cursor: pointer; margin-bottom: 0; border-bottom: 1px solid var(--border);
        padding-bottom: .3rem; font-size: .65rem;
      }}
      .filter-section > summary::after {{ content: "▾"; font-size: .7rem; margin-left: auto; }}
      .filter-section[open] > summary {{ margin-bottom: .6rem; }}
      .filter-section[open] > summary::after {{ content: "▴"; }}
      .panel-rss {{ left: 1rem; right: 1rem; top: 100%; width: auto; }}
      main {{ padding: 1rem; }}
    }}
  </style>
</head>
<body>
  <div class="sticky-top">
    <header>
      <div class="brand">
        {SVG_LOGO}
        <div>
          <h1>CEP Radar</h1>
          <p>Última actualización: {dt}</p>
        </div>
      </div>
      <a class="dev-credit" href="https://elprofedelabata.es" target="_blank" rel="noopener">
        <div class="dev-credit-text">
          <span class="dev-credit-label">Desarrollado por</span>
          <span class="dev-credit-name">El Profe de la Bata</span>
          <span class="dev-credit-url">elprofedelabata.es</span>
        </div>
        {SVG_AVATAR}
      </a>
      <p class="header-tagline">Todas las actividades formativas de los Centros del Profesorado de Andalucía, actualizadas cada día de forma automática.</p>
    </header>

    <div class="toolbar">
      <div class="toolbar-left">
        <div class="search-wrap">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9.5 16q-2.725 0-4.612-1.888T3 9.5t1.888-4.612T9.5 3t4.613 1.888T16 9.5q0 1.1-.35 2.075T14.7 13.3l5.6 5.6q.275.275.275.7t-.275.7t-.7.275t-.7-.275l-5.6-5.6q-.75.6-1.725.95T9.5 16m0-2q1.875 0 3.188-1.312T14 9.5t-1.312-3.187T9.5 5T6.313 6.313T5 9.5t1.313 3.188T9.5 14"/></svg>
          <input id="filtroTexto" type="search" placeholder="Buscar por título..."
                 oninput="filtrar()">
        </div>
        <button class="btn-filtrar" onclick="toggleFiltros()" aria-expanded="false"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M20 2H4c-.55 0-1 .45-1 1v2c0 .24.09.48.25.66L10 13.38V21c0 .4.24.77.62.92a.995.995 0 0 0 1.09-.21l2-2A1 1 0 0 0 14 19v-5.62l6.75-7.72c.16-.18.25-.42.25-.66V3c0-.55-.45-1-1-1"/></svg><span class="btn-txt"> Filtrar</span></button>
      </div>
      <button class="btn-rss" onclick="toggleRss()" aria-expanded="false">{SVG_RSS}<span class="btn-txt"> RSS</span></button>
      {rss_panel}
      {panel}
    </div>
  </div>

  <div id="toast"></div>

  <main>
    <p class="results-summary" id="contador">Mostrando {total} de {total} actividades</p>
    <div class="grid" id="grid">
      {cards}
      <p id="sin-resultados">No hay actividades que coincidan con los filtros.</p>
    </div>
  </main>

  <script>
    let toastTimer;
    function copiarRSS(ruta) {{
      const url = new URL(ruta, window.location.href).href;
      navigator.clipboard.writeText(url).then(() => {{
        const t = document.getElementById('toast');
        t.textContent = '✓ URL copiada — pégala en tu lector RSS (Feedly, Inoreader...)';
        t.classList.add('visible');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => t.classList.remove('visible'), 3500);
      }});
    }}

    function cerrarPanel(idPanel, selectorBoton) {{
      const panel = document.getElementById(idPanel);
      const btn = document.querySelector(selectorBoton);
      panel.classList.add('hidden');
      btn.classList.remove('activo');
      btn.setAttribute('aria-expanded', 'false');
    }}

    function toggleRss() {{
      const panel = document.getElementById('panel-rss');
      const btn = document.querySelector('.btn-rss');
      const abrir = panel.classList.contains('hidden');
      cerrarPanel('panel-filtros', '.btn-filtrar');
      panel.classList.toggle('hidden', !abrir);
      btn.classList.toggle('activo', abrir);
      btn.setAttribute('aria-expanded', abrir ? 'true' : 'false');
    }}

    function toggleFiltros() {{
      const panel = document.getElementById('panel-filtros');
      const btn   = document.querySelector('.btn-filtrar');
      const abrir = panel.classList.contains('hidden');
      cerrarPanel('panel-rss', '.btn-rss');
      panel.classList.toggle('hidden', !abrir);
      btn.classList.toggle('activo', abrir);
      btn.setAttribute('aria-expanded', abrir ? 'true' : 'false');
    }}

    function filtrar() {{
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
      const texto   = document.getElementById('filtroTexto').value.toLowerCase();
      const ceps     = [...document.querySelectorAll('.f-cep:checked')].map(c => c.value);
      const modals   = [...document.querySelectorAll('.f-modal:checked')].map(c => c.value);
      const dirigidos = [...document.querySelectorAll('.f-dirigido:checked')].map(c => c.value);
      const estados  = [...document.querySelectorAll('.f-estado:checked')].map(c => c.value);

      const cards = document.querySelectorAll('.card');
      const total = cards.length;
      let visibles = 0;
      cards.forEach(c => {{
        const ok = (!ceps.length      || ceps.includes(c.dataset.cep))
                && (!modals.length    || modals.includes(c.dataset.modalidad))
                && (!dirigidos.length || dirigidos.includes(c.dataset.dirigido))
                && (!estados.length   || estados.includes(c.dataset.estado))
                && (!texto            || c.textContent.toLowerCase().includes(texto));
        c.classList.toggle('hidden', !ok);
        if (ok) visibles++;
      }});
      document.getElementById('contador').textContent =
        'Mostrando ' + visibles + ' de ' + total + ' actividades';
      document.getElementById('sin-resultados').style.display =
        visibles === 0 ? 'block' : 'none';
    }}
  </script>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Generando sitio estático ===\n")

    with open(os.path.join(DATA_DIR, "actividades.json"), encoding="utf-8") as f:
        datos = json.load(f)

    vistas_path = os.path.join(DATA_DIR, "vistas.json")
    vistas = {}
    if os.path.exists(vistas_path):
        with open(vistas_path, encoding="utf-8") as f:
            vistas = json.load(f)

    actividades = datos["actividades"]
    generado = datos["generado"]

    os.makedirs(DOCS_DIR, exist_ok=True)

    por_cep = generar_rss(actividades, vistas)

    html = generar_html(actividades, por_cep, generado)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Web: {DOCS_DIR}/index.html ({len(actividades)} actividades)")


if __name__ == "__main__":
    main()
