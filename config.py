"""
Configuración central del scraper de ListEngine (https://www.listengine.online).

Contiene todos los valores predeterminados del scrapper, todos estos se pueden cambiar desde la
línea de comandos (python main.py --help) sin editar este archivo.
"""

# --- Sitio ---------------------------------------------------------------
URL_BASE = "https://www.listengine.online"
URL_EVENTOS = URL_BASE + "/events"
IDIOMA = "en-US"

# --- Identificación (la práctica exige comprobar el User-Agent) ----------
# UA honesto que identifica el propósito.
USER_AGENT = "UOC-Practica1-Scraper/1.0 (proyecto academico; contacto: tu_correo@ejemplo.com)"
HEADLESS = True

# --- Uso responsable (sitio pequeño: no saturarlo) -----------------------
PAUSA_MIN = 3.0           # segundos mínimos entre peticiones
PAUSA_MAX = 6.0           # la pausa es aleatoria dentro del rango
REINTENTOS = 3            # reintentos por URL, con espera exponencial
MAX_PETICIONES = 2000     # tope duro de páginas cargadas por ejecución

# --- Qué eventos descargar -----------------------------------------------
FECHA_MIN = "2026-01-01"  # AAAA-MM-DD; None = sin límite
FECHA_MAX = None          # AAAA-MM-DD; None = sin límite
MIN_JUGADORES = 0         # descarta eventos con menos jugadores (p. ej. 20)
FILTRO_NOMBRE = None      # regex sobre el nombre del evento, p. ej. r"\bGT\b|Grand Tournament"
FILTRO_JUGADORES_WEB = None   # filtro propio de la web "Number of Players": "+20", "+50" o "+100"
MAX_EVENTOS = 50

# --- Qué se descarga de cada evento --------------------------------------
MAX_LISTAS_POR_EVENTO = 10    # listas de los mejores clasificados; None = todas
MAX_EXPANSIONES = 15          # veces que se pulsa "load more / next" dentro de un evento

# Texto que indicaría contenido restringido (solo se anota, nunca se intenta sortear)
PISTAS_BLOQUEO = r"subscribe to|subscribers? only|subscription required|requires? (?:a )?subscription|upgrade to|premium"

# --- Salida --------------------------------------------------------------
ANONIMIZAR = True         # True: no se guarda el nombre del jugador, solo un hash (RGPD)
DIR_SALIDA = "salida"
SALIDA_JSONL = DIR_SALIDA + "/eventos_raw.jsonl"   # un evento por línea (permite reanudar)
SALIDA_JSON = DIR_SALIDA + "/eventos_raw.json"     # volcado final en JSON bruto
