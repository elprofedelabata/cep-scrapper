import requests
from bs4 import BeautifulSoup

BASE_URL = "https://secretariavirtual.juntadeandalucia.es/secretariavirtual/consultaCEP"
SEARCH_URL = f"{BASE_URL}/buscar/"

# Valores válidos para los campos select (para referencia)
CENTROS = {
    "-1": "Cualquiera",
    "5239": "CEP Almería", "5240": "CEP El Ejido", "5241": "CEP Cuevas - Olula",
    "5242": "CEP Cádiz", "5243": "CEP Jerez de la Frontera", "5244": "CEP Villamartín",
    "5245": "CEP Algeciras - La Línea", "5246": "CEP Córdoba", "5247": "CEP Peñarroya-Pueblonuevo",
    "5248": "CEP Priego - Montilla", "5249": "CEP Granada", "5250": "CEP Motril",
    "5251": "CEP Guadix", "5252": "CEP Baza", "5253": "CEP Huelva - Isla Cristina",
    "5254": "CEP Bollullos - Valverde", "5255": "CEP Aracena", "5256": "CEP Jaén",
    "5257": "CEP Linares - Andújar", "5258": "CEP Úbeda", "5259": "CEP Orcera",
    "47949": "CEP Innovación FP", "5260": "CEP Málaga", "5261": "CEP Marbella - Coín",
    "5262": "CEP Ronda", "5263": "CEP Antequera", "5264": "CEP Vélez-Málaga",
    "5265": "CEP Sevilla", "5266": "CEP Castilleja de la Cuesta", "5267": "CEP Osuna - Écija",
    "5268": "CEP Mairena del Alcor", "5269": "CEP Lebrija", "5270": "CEP Lora del Río",
}

ESTADOS = {
    "-1": "Cualquiera",
    "5": "En proyecto",
    "6": "Abierto plazo solicitudes",
    "7": "Finalizado plazo solicitudes",
    "4": "Publicadas Listas Provisionales",
    "8": "Publicadas Listas Definitivas",
    "2": "Actividad en desarrollo",
    "3": "Terminada",
}

MODALIDADES = {
    "-1": "Cualquiera",
    "8": "Conferencia", "6": "Congreso", "1": "Curso", "3": "Curso a Distancia",
    "4": "Curso con Seguimiento", "2": "Curso Semipresencial", "7": "Encuentro",
    "10": "Formación en centros", "12": "Formación Específica en Centros",
    "9": "Grupos de trabajo", "5": "Jornadas", "53": "Mentor", "11": "Otros", "52": "Visitante",
}


def crear_sesion():
    session = requests.Session()
    session.get(BASE_URL + "/", timeout=15)
    return session


def buscar_actividades(session, filtros=None):
    """
    Busca actividades aplicando los filtros indicados.

    filtros: dict con cualquiera de estas claves:
        centro      — ID del CEP (ver CENTROS)
        modalidad   — ID de modalidad (ver MODALIDADES), puede ser lista para múltiples
        dirigido    — ID del nivel educativo
        estado      — ID del estado (ver ESTADOS)
        fechaI      — fecha inicio en formato dd/mm/aaaa
        fechaF      — fecha fin en formato dd/mm/aaaa
        titulo      — texto libre
        codigoEdicion
        descriptor  — ID del descriptor
    """
    payload = {
        "centro": "-1",
        "modalidad": "-1",
        "_modalidad": "1",
        "dirigido": "-1",
        "estado": "-1",
        "fechaI": "",
        "fechaF": "",
        "titulo": "",
        "codigoEdicion": "",
        "descriptor": "-1",
    }
    if filtros:
        payload.update(filtros)

    # El servidor falla o agota el tiempo si no hay ningún filtro restrictivo
    if all(payload.get(k) in ("-1", "") for k in ("centro", "estado", "titulo", "codigoEdicion")):
        raise ValueError("Aplica al menos un filtro: centro, estado, titulo o codigoEdicion")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": BASE_URL + "/",
    }

    response = session.post(SEARCH_URL, data=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.text


def parsear_actividades(html):
    """Devuelve lista de dicts con los datos de cada actividad."""
    soup = BeautifulSoup(html, "html.parser")
    tabla = soup.find("table", id="tableCEP")
    if not tabla:
        return []

    cabeceras = [th.get_text(strip=True) for th in tabla.find("thead").find_all("th")]

    actividades = []
    for fila in tabla.find("tbody").find_all("tr"):
        celdas = [td.get_text(strip=True) for td in fila.find_all("td")]
        if not celdas:
            continue
        a = dict(zip(cabeceras, celdas))
        # Extraer URL de detalle del enlace en la celda del título
        enlace = fila.find("a", href=True)
        a["URL"] = enlace["href"] if enlace else ""
        actividades.append(a)

    return actividades


def obtener_actividades(filtros=None):
    """Crea sesión, busca y parsea en un solo paso."""
    session = crear_sesion()
    html = buscar_actividades(session, filtros)
    return parsear_actividades(html)


if __name__ == "__main__":
    actividades = obtener_actividades({"estado": "6"})
    print(f"Actividades con plazo abierto: {len(actividades)}")
    for a in actividades[:3]:
        print(f"\n{a['Código']} — {a['Título']}")
        print(f"  {a['CEP']} | {a['Modalidad']} | {a['Inicio']} → {a['Fin']}")
