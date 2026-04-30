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
    "Abierto plazo solicitudes":       "#d8315b",  # magenta-bloom — acción inmediata
    "En proyecto":                     "#3e92cc",  # blue-bell
    "Finalizado plazo solicitudes":    "#0a2463",  # imperial-blue
    "Actividad en desarrollo":         "#1a6b3c",  # verde propio
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

SVG_LOGO = ('<svg class="site-logo" xmlns="http://www.w3.org/2000/svg" '
            'xml:space="preserve" viewBox="0 0 14.26 14.26" aria-hidden="true" focusable="false">'
            '<circle cx="7.13" cy="7.13" r="7.13" fill="var(--ghost-white)"/>'
            '<path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M7.01.01C5.22.12 4.03.58 2.7 1.54c-.18.14-.68.59-.81.74-.04.04-.06.08-.11.12C1.3 2.91.85 3.65.57 4.29c-.81 1.82-.74 4.01.1 5.81.35.75 1.04 1.74 1.71 2.29l.24.21c.4.35 1.14.79 1.65 1.03.84.4 1.91.64 3 .63 1.07-.01 2.1-.3 2.91-.7.66-.33 1.1-.62 1.61-1.06.09-.08.16-.13.24-.21.09-.1.14-.13.22-.22.34-.42.39-.4.79-.98.24-.35.45-.74.63-1.15.36-.86.62-1.9.59-2.94-.04-1.53-.45-2.79-1.28-4-.14-.2-.25-.32-.39-.5l-.32-.36c-.32-.31-.71-.66-1.09-.91-.35-.23-.72-.46-1.16-.63C9.17.25 8.06-.06 7.01.01zM4.63 10.72c-.02.01 0 .01-.04.02l-.39.03c-.15.02-.31.04-.45.07l-.45 1.92c1.09-.18 2.23-.08 3.16.49.29.17.5.36.71.54.03-.03.04-.04.08-.07.34-.36 1.01-.68 1.49-.84.88-.28 1.42-.21 2.25-.13l-.46-1.91c-.14-.03-.75-.1-.79-.12.07-.06.37-.17.46-.23.07-.04.11-.14.08-.26-.02-.11-.09-.13-.19-.18-.63-.28-1.34-.64-1.95-.91-1.18-.52-.77-.52-1.49-.21-.69.3-1.78.81-2.46 1.14-.19.09-.24.31-.05.42.16.09.34.15.49.23zm4.08.34c-.27.08-1.4.73-1.55.7-.15-.02-1.43-.72-1.56-.71 0 .96-.21.74 1.04 1.33.6.28.36.44.75.19.23-.16.53-.31.8-.43.64-.28.52-.24.52-1.08zm-4.06-.76c.75.35 1.51.72 2.25 1.08.35.17.22.17.57.01.19-.09.38-.18.56-.27.19-.1.37-.19.57-.28.09-.04.18-.08.27-.13.09-.05.2-.08.28-.13v.61c-.02.07-.06.06-.08.15-.01.08.03.08.03.16s-.12.47-.08.55c.03.05 0 .03.08.06.12.05.28.04.36-.04.06-.07-.02-.38-.05-.49-.05-.18.05-.14.01-.27-.04-.11-.08-.01-.08-.23v-.6l.35-.17c-.05-.07-2.49-1.2-2.52-1.2-.07.01-2.47 1.15-2.52 1.19zm6.16-5.28c.2.25.41.75.52 1.1.36 1.15.17 2.3-.41 3.33-.11.2-.24.33-.35.49.03.07.07.15.11.2.28-.34.46-.62.68-1.09.51-1.11.46-2.5-.07-3.61l-.3-.56c.04-.08.24-.19.33-.26.11-.07.24-.16.35-.24.1-.07.64-.47.72-.48.33.5.65 1.29.78 1.97.37 1.95-.12 3.8-1.38 5.3l-.7.71c.02.1.09.45.14.51.9-.72 1.67-1.66 2.2-3.08.51-1.36.51-3.12-.01-4.48-.27-.71-.52-1.16-.92-1.71-.36-.5-.82-.95-1.32-1.33C8.81 0 5.53.07 3.12 1.81c-.07.05-.11.09-.18.15l-.36.3c-.25.22-.6.59-.8.86C.48 4.89.08 7.24.85 9.3c.33.89.44 1.01.91 1.72.06.11.51.65.6.73.14.12.22.2.34.32.03.04.31.27.38.31l.12-.5-.72-.72c-.68-.75-1.19-1.88-1.4-2.92-.35-1.82.26-3.77 1.28-4.98.13-.15.37-.44.52-.56.73-.66 1.53-1.16 2.57-1.45.86-.24 1.72-.29 2.64-.18.72.09 1.64.42 2.16.76 0 .07-.14.3-.19.39-.08.13-.15.25-.22.39-.06.1-.41.74-.45.76-.25-.07-.49-.26-1.07-.4-1.07-.27-2.14-.15-3.14.3-.18.08-.31.17-.47.25-.09-.02-.33-.23-.64-.01-.27.2-.12.52-.11.61-.04.05-.08.08-.13.13-.06.05-.07.08-.13.14-.19.19-.52.7-.64.95-.25.54-.4.98-.46 1.64-.12 1.28.41 2.43 1.04 3.15l.06-.08c.02-.04.03-.05.05-.09-.12-.24-.39-.41-.71-1.27-.52-1.4-.16-3.09.82-4.17l.24-.26c.1.01.13.06.29.06.11 0 .2-.04.27-.09.2-.14.17-.27.17-.53.61-.36 1.29-.62 2.14-.66.79-.04 1.73.17 2.3.51.03.06-.02.09-.07.18-.03.06-.08.13-.11.19L8.5 4.97c-.03.05-.02.05-.06.07-.24-.07-.35-.21-.9-.29-2.05-.29-3.76 1.81-2.81 3.79.14.29.2.33.36.53.05.06.09.09.15.14l.18-.08a.436.436 0 0 0-.13-.14c-.31-.3-.56-.92-.61-1.34-.11-1.18.62-2.26 1.79-2.61.6-.18 1.36-.1 1.85.18.04.07-.1.24-.17.37-.08.13-.15.25-.22.38l-.38.66c-.03.05-.02.05-.08.07-.22-.05-.34-.09-.58 0-.54.21-.7.89-.25 1.29.27.25.74.27 1.03.03.23-.19.41-.61.19-.98.03-.06.08-.08.16-.13l.53-.37c.11-.07.23-.15.34-.23.08-.06.28-.22.37-.23.28.47.44 1.01.36 1.66-.07.54-.42 1.12-.72 1.36.05.06.14.1.2.11.77-.76 1.05-2.17.33-3.24.02-.06 0-.03.07-.09l.95-.65c.06-.04.11-.08.17-.12.06-.04.12-.09.19-.09z"/>'
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
         data-estado="{slug(a.get('Estado',''))}">
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

    # Modalidades y estados únicos presentes en los datos
    modalidades = sorted({a.get("Modalidad", "") for a in actividades if a.get("Modalidad")})
    estados     = sorted({a.get("Estado", "")    for a in actividades if a.get("Estado")})

    modal_items  = "".join(
        f'<label><input type="checkbox" class="f-modal" value="{slug(m)}" onchange="filtrar()"> {m}</label>'
        for m in modalidades
    )
    estado_items = "".join(
        f'<label><input type="checkbox" class="f-estado" value="{slug(e)}" onchange="filtrar()"> {e}</label>'
        for e in estados
    )

    return f"""
  <div id="panel-filtros" class="panel-filtros hidden">
    <section>
      <h4>{SVG_CEP} Centros de Educación del Profesorado, CEP's</h4>
      <div class="cep-grid">{cep_cols}</div>
    </section>
    <section>
      <h4>{SVG_MODAL} Modalidad</h4>
      <div class="opciones-row">{modal_items}</div>
    </section>
    <section>
      <h4>{SVG_ESTADO} Estado</h4>
      <div class="opciones-row">{estado_items}</div>
    </section>
  </div>"""


def panel_rss_html(por_cep):
    por_provincia = defaultdict(list)
    for cep in sorted(por_cep.keys()):
        por_provincia[provincia_de_cep(cep)].append(cep)

    rss_cols = ""
    for prov in sorted(por_provincia, key=lambda p: PROVINCIA_NOMBRE.get(p, p)):
        nombre_prov = PROVINCIA_NOMBRE.get(prov, prov)
        items = "".join(
            f'<a href="rss/{slug(nombre_cep(c))}.xml">'
            f'<span>{nombre_cep(c)}</span></a>'
            for c in por_provincia[prov]
        )
        rss_cols += f'<div class="rss-prov-col"><strong>{nombre_prov}</strong>{items}</div>'

    return f"""
  <div id="panel-rss" class="panel-rss hidden">
    <section>
      <h4>{SVG_RSS} Feeds RSS</h4>
      <a class="rss-primary" href="rss/todas.xml">
        <span>Todas las actividades</span>
      </a>
    </section>
    <section>
      <h4>Por CEP</h4>
      <div class="rss-grid">{rss_cols}</div>
    </section>
  </div>"""


def generar_html(actividades, por_cep, generado):
    cards = "\n".join(card_html(a) for a in actividades)
    panel = panel_filtros_html(por_cep, actividades)
    rss_panel = panel_rss_html(por_cep)
    dt    = datetime.fromisoformat(generado).strftime("%d/%m/%Y %H:%M UTC")
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
      --imperial-blue: #0a2463;
      --blue-bell:     #3e92cc;
      --ghost-white:   #fffaff;
      --magenta-bloom: #d8315b;
      --text:          #1a1a2e;
      --text-muted:    #5a5a72;
      --border:        #dde3f0;
      --bg:            #f0f2f8;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: "Domine", Georgia, serif; background: var(--bg); color: var(--text); }}
    input, button {{ font: inherit; }}

    header {{
      background: var(--imperial-blue);
      color: var(--ghost-white);
      padding: 1.5rem 2rem;
      border-bottom: 4px solid var(--magenta-bloom);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1.5rem;
      position: relative;
      z-index: 20;
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
      color: var(--imperial-blue);
    }}
    header h1 {{ font-size: 1.4rem; letter-spacing: .01em; }}
    header p {{ font-size: .85rem; opacity: .75; margin-top: .25rem; }}
    .header-rss {{
      background: rgba(255,255,255,.12);
      border: 1px solid rgba(255,255,255,.22);
      color: var(--ghost-white);
    }}
    .header-rss:hover {{ background: rgba(255,255,255,.2); }}
    .header-rss.activo {{ background: var(--magenta-bloom); border-color: var(--magenta-bloom); }}

    .toolbar {{
      background: var(--ghost-white);
      padding: .85rem 2rem;
      display: flex; gap: .75rem; align-items: center; flex-wrap: wrap;
      border-bottom: 1px solid var(--border);
      box-shadow: 0 1px 4px rgba(10,36,99,.06);
      position: relative;
    }}
    .toolbar input {{
      flex: 1; min-width: 200px;
      padding: .45rem .75rem;
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
    .btn-filtrar:hover {{ background: var(--blue-bell); }}
    .btn-filtrar.activo {{ background: var(--magenta-bloom); }}
    .panel-filtros {{
      background: white;
      border-bottom: 1px solid var(--border);
      padding: 1.25rem 2rem;
      box-shadow: 0 4px 12px rgba(10,36,99,.08);
    }}
    .panel-filtros.hidden, .panel-rss.hidden {{ display: none; }}
    .panel-filtros section, .panel-rss section {{ margin-bottom: 1.1rem; }}
    .panel-filtros section:last-child, .panel-rss section:last-child {{ margin-bottom: 0; }}
    .panel-filtros h4, .panel-rss h4 {{
      font-size: .75rem; text-transform: uppercase;
      letter-spacing: .08em; color: var(--text-muted);
      margin-bottom: .6rem; padding-bottom: .3rem;
      border-bottom: 1px solid var(--border);
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
      top: calc(50% + 1.55rem);
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
    .rss-primary {{
      display: inline-flex; align-items: center; gap: .5rem;
      color: var(--imperial-blue); background: #edf6ff;
      padding: .4rem .75rem; border-radius: 6px;
      text-decoration: none; font-size: .8rem; font-weight: 700;
    }}
    .rss-grid {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: .5rem 1rem; overflow-x: auto; }}
    .rss-prov-col {{ display: flex; flex-direction: column; gap: .3rem; min-width: 0; }}
    .rss-prov-col strong {{
      font-size: .72rem; text-transform: uppercase;
      letter-spacing: .06em; color: var(--imperial-blue);
      margin-bottom: .15rem;
    }}
    .rss-prov-col a {{
      display: flex; align-items: center; justify-content: space-between; gap: .5rem;
      color: var(--text); text-decoration: none; font-size: .75rem;
      overflow: hidden;
    }}
    .rss-prov-col a span {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }}
    .rss-primary:hover, .rss-prov-col a:hover {{ color: var(--blue-bell); }}

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
      header {{ align-items: flex-start; flex-direction: column; gap: .9rem; }}
      .header-rss {{ align-self: flex-end; }}
      .panel-rss {{ left: 1rem; right: 1rem; top: calc(100% + .15rem); width: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">
      {SVG_LOGO}
      <div>
        <h1>CEP Radar</h1>
        <p>Última actualización: {dt} · {total} actividades</p>
      </div>
    </div>
    <button class="btn-rss header-rss" onclick="toggleRss()" aria-expanded="false">{SVG_RSS} RSS</button>
    {rss_panel}
  </header>

  <div class="toolbar">
    <input id="filtroTexto" type="search" placeholder="Buscar por título..."
           oninput="filtrar()">
    <button class="btn-filtrar" onclick="toggleFiltros()" aria-expanded="false">⚙ Filtrar</button>
  </div>
  {panel}

  <main>
    <p class="results-summary" id="contador">Mostrando {total} de {total} actividades</p>
    <div class="grid" id="grid">
      {cards}
      <p id="sin-resultados">No hay actividades que coincidan con los filtros.</p>
    </div>
  </main>

  <script>
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
      const texto   = document.getElementById('filtroTexto').value.toLowerCase();
      const ceps    = [...document.querySelectorAll('.f-cep:checked')].map(c => c.value);
      const modals  = [...document.querySelectorAll('.f-modal:checked')].map(c => c.value);
      const estados = [...document.querySelectorAll('.f-estado:checked')].map(c => c.value);

      const cards = document.querySelectorAll('.card');
      const total = cards.length;
      let visibles = 0;
      cards.forEach(c => {{
        const ok = (!ceps.length    || ceps.includes(c.dataset.cep))
                && (!modals.length  || modals.includes(c.dataset.modalidad))
                && (!estados.length || estados.includes(c.dataset.estado))
                && (!texto          || c.textContent.toLowerCase().includes(texto));
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
