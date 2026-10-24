"""
Descubrimiento y extracción de ListEngine (https://www.listengine.online), sin usar API.

Estructura de la web (contenido dinámico, Vue/Nuxt):
  /events        tarjetas de evento (nombre, fecha, nº de jugadores, top 3), 20 por página,
                 paginación con botones Previous / 1..5 / Next
  /events/<id>   todos los jugadores; cada fila es un enlace a /lists/<id> con rango,
                 jugador, ejército, destacamento(s), disposición y resultado W-L-D
  /lists/<id>    lista del jugador (se guarda su texto bruto; se parsea en normalizar.py)

Flujo: listado paginado -> (filtros) -> cada evento -> sus listas.
"""
import re
import time
from datetime import datetime, timezone

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import config
from dom import buscar_por_texto, clic, scroll_final

META_EVENTOS = {}   # url_evento -> metadatos leídos de la tarjeta del listado

# JavaScript que se ejecuta en el navegador para leer el DOM de una sola vez
JS_TARJETAS = """
return [...document.querySelectorAll('.event-card')].map(c => {
  const t = s => { const e = c.querySelector(s); return e ? e.innerText.trim() : null; };
  const ver = c.querySelector("a[href^='/events/']");
  return {nombre: t('h2'), jugadores: t('p.italic'), fecha: t('p.text-xs'),
          href: ver ? ver.href : null};
});
"""
JS_FILAS = ("return [...document.querySelectorAll(\"a[href*='/lists/']\")]"
            ".map(a => ({href: a.href, texto: a.innerText.trim()}));")
JS_PRIMER_EVENTO = "const e = document.querySelector('.event-card h2'); return e ? e.innerText : null;"

RE_RANGO = re.compile(r"^#(\d+)$")
RE_WLD = re.compile(r"^(\d+)-(\d+)-(\d+)$")
RE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------- Utilidades ----------

def _esperar(driver, css, timeout=20):
    """Espera a que aparezca algún elemento (la app Vue pinta el contenido tras cargar)."""
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.find_elements(By.CSS_SELECTOR, css))
        return True
    except TimeoutException:
        return False


def _rechazar_cookies(driver):
    """Pulsa 'Decline' en el banner propio del sitio (solo cookies esenciales)."""
    boton = buscar_por_texto(driver, "decline", exacto=True)
    if boton is not None:
        clic(driver, boton)
        time.sleep(0.5)
        print("[listengine] cookies opcionales rechazadas")


def parsear_fila(texto):
    """Texto visible de la fila de un jugador -> dict.

    Orden de escritorio: #rango, jugador, ejército, destacamento(s), disposición, W-L-D.
    Rango y W-L-D se reconocen por su forma, así que el orden entre ellos no importa.
    """
    p = {"posicion": None, "victorias": None, "derrotas": None, "empates": None,
         "jugador": None, "faccion": None, "destacamento": None, "destacamentos": [],
         "disposicion_fuerzas": None}
    resto = []
    for linea in (l.strip() for l in texto.split("\n")):
        if not linea:
            continue
        if (m := RE_RANGO.match(linea)):
            p["posicion"] = int(m.group(1))
        elif (m := RE_WLD.match(linea)):
            p["victorias"], p["derrotas"], p["empates"] = map(int, m.groups())
        else:
            resto.append(linea)
    for clave, valor in zip(("jugador", "faccion", "destacamento", "disposicion_fuerzas"), resto):
        p[clave] = valor
    if p["destacamento"]:   # en 11ª pueden ser varios, separados por comas
        p["destacamentos"] = [x.strip() for x in p["destacamento"].split(",") if x.strip()]
    return p


# ---------- Fase 1: descubrimiento (listado paginado + filtros) ----------

def _cumple(meta):
    """Aplica los filtros de config.py a los metadatos de una tarjeta."""
    f = meta.get("fecha")
    if config.FECHA_MIN and f and f < config.FECHA_MIN:
        return False
    if config.FECHA_MAX and f and f > config.FECHA_MAX:
        return False
    if (meta.get("n_jugadores") or 0) < config.MIN_JUGADORES:
        return False
    if config.FILTRO_NOMBRE and not re.search(config.FILTRO_NOMBRE, meta.get("nombre") or "", re.I):
        return False
    return True


def _pagina_siguiente(nav):
    """Pulsa 'Next' y espera a que cambie la primera tarjeta. False si no hay más páginas."""
    d = nav.driver
    boton = buscar_por_texto(d, "next", exacto=True)
    if boton is None or boton.get_attribute("disabled") is not None:
        return False
    primero = d.execute_script(JS_PRIMER_EVENTO)
    nav.pausa()
    clic(d, boton)
    for _ in range(20):
        time.sleep(0.5)
        if d.execute_script(JS_PRIMER_EVENTO) != primero:
            return True
    return False


def descubrir_eventos(nav):
    """Recorre el listado página a página. Devuelve [(url_evento, resumen), ...]."""
    d = nav.driver
    nav.abrir(config.URL_EVENTOS)
    if not _esperar(d, ".event-card"):
        print("[listengine] no aparecen tarjetas de evento")
        return []
    _rechazar_cookies(d)
    if config.FILTRO_JUGADORES_WEB:                      # filtro "Number of Players" de la propia web
        for texto in (config.FILTRO_JUGADORES_WEB, "filter events"):
            b = buscar_por_texto(d, texto, exacto=True)
            if b is not None:
                clic(d, b)
                time.sleep(1.5)

    aceptados, vistos, pagina = [], set(), 1
    while True:
        fechas = []
        for t in d.execute_script(JS_TARJETAS):
            if not t["href"] or t["href"] in vistos:
                continue
            vistos.add(t["href"])
            n = re.search(r"\d+", t["jugadores"] or "")
            meta = {"url": t["href"], "nombre": t["nombre"],
                    "n_jugadores": int(n.group()) if n else None,
                    "fecha": t["fecha"] if RE_ISO.match(t["fecha"] or "") else None}
            fechas.append(meta["fecha"])
            if _cumple(meta):
                META_EVENTOS[t["href"]] = meta
                aceptados.append(meta)
        print(f"[listengine] página {pagina}: {len(aceptados)} eventos aceptados en total")
        if len(aceptados) >= config.MAX_EVENTOS:
            break
        # El listado va de más reciente a más antiguo: si toda la página queda fuera del rango, se para
        if config.FECHA_MIN and fechas and all(f and f < config.FECHA_MIN for f in fechas):
            break
        if not _pagina_siguiente(nav):
            break
        pagina += 1
    return [(m["url"], f"{m['fecha']} | {m['n_jugadores']} jugadores | {m['nombre']}")
            for m in aceptados[:config.MAX_EVENTOS]]


# ---------- Fase 2: evento (todos los jugadores) y listas ----------

def _boton_expansion(driver):
    for texto in ("load more", "show more", "next"):
        b = buscar_por_texto(driver, texto, exacto=True)
        if b is not None and b.get_attribute("disabled") is None:
            return b
    return None


def _recoger_filas(nav):
    """Filas de jugadores del evento; expande 'load more / show more / next' si existen."""
    d = nav.driver
    filas = {}
    for _ in range(config.MAX_EXPANSIONES):
        scroll_final(d, 10)
        antes = len(filas)
        for a in d.execute_script(JS_FILAS):
            filas.setdefault(a["href"], a["texto"])
        if antes > 0 and len(filas) == antes:      # ya no aparecen filas nuevas
            break
        boton = _boton_expansion(d)
        if boton is None:
            break
        nav.pausa()
        clic(d, boton)
        time.sleep(1.5)
    return filas


def _capturar_lista(nav, participante):
    d = nav.driver
    try:
        nav.abrir(participante["lista_url"])
    except PermissionError as e:
        print(f"   [listas] {e}")
        return None
    fin = time.time() + 12                    # el contenido llega después de cargar la app
    while time.time() < fin and len(d.find_element(By.TAG_NAME, "body").text) < 200:
        time.sleep(0.5)
    scroll_final(d, 5)
    texto = d.find_element(By.TAG_NAME, "body").text
    return {"jugador": participante["jugador"], "url": participante["lista_url"],
            "titulo_pagina": d.title, "texto": texto,
            "posible_contenido_restringido": bool(re.search(config.PISTAS_BLOQUEO, texto, re.I))}


def extraer_evento(nav, url, resumen=""):
    """Descarga un evento: sus participantes y las listas de los mejor clasificados."""
    d = nav.driver
    nav.abrir(url)
    _esperar(d, "a[href*='/lists/']")
    _rechazar_cookies(d)

    participantes = []
    for href, texto in _recoger_filas(nav).items():
        p = parsear_fila(texto)
        p["lista_url"] = href
        participantes.append(p)
    participantes.sort(key=lambda p: (p["posicion"] is None, p["posicion"] or 0))

    meta = META_EVENTOS.get(url, {})
    evento = {
        "fuente": "listengine", "url": url, "nombre": meta.get("nombre"),
        "fecha": meta.get("fecha"), "n_jugadores": meta.get("n_jugadores"),
        "titulo_pagina": d.title, "user_agent": nav.ua,
        "capturado_en": datetime.now(timezone.utc).isoformat(),
        "participantes": participantes,
        "texto_completo": d.find_element(By.TAG_NAME, "body").text,
        "listas_brutas": [],
    }
    tope = config.MAX_LISTAS_POR_EVENTO
    for i, p in enumerate(participantes[:tope] if tope else participantes, 1):
        item = _capturar_lista(nav, p)
        if item:
            evento["listas_brutas"].append(item)
        if i % 10 == 0:
            print(f"   [listas] {i} listas descargadas")
    print(f"   participantes: {len(participantes)} | listas: {len(evento['listas_brutas'])}")
    return evento
