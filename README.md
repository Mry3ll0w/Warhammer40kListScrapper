# Torneos competitivos de Warhammer 40,000 (11ª edición, 2026): scraper de ListEngine

Práctica 1 · M2.851 Tipología y ciclo de vida de los datos · Máster Universitario en Ciencia de Datos (UOC)

Script de *web scraping* (Python + Selenium) que genera un dataset de torneos de Warhammer 40,000 a partir de
[ListEngine](https://www.listengine.online): resultados de todos los participantes (puesto, facción,
destacamentos, disposición de fuerzas, victorias-derrotas-empates) y listas de ejército completas
(unidades con su coste en puntos y mejoras).

## 1. Integrantes del grupo

- Antonio Roldán Andrade

## 2. Enlaces y DOI del dataset

| Elemento | Enlace |
|---|---|
| DOI del dataset en Zenodo | https://doi.org/10.5281/zenodo.23622330 |
| Sitio web extraído | https://www.listengine.online |
| Vídeo explicativo (Google Drive UOC) | [COMPLETAR: https://drive.google.com/…] |

## 3. Archivos del repositorio

```
.
├── README.md             
├── requirements.txt      Librerías necesarias
├── .gitignore            Excluye los datos brutos (anonimizado de nombres de jugadores)
├── source/               Código Python
│   ├── main.py           Punto de entrada: descubre eventos, descarga datos y genera los CSV
│   ├── config.py         Configuración de parametros de ejecucion (sitio, filtros, pausas, salidas)
│   ├── navegador.py      Selenium con User-Agent propio, robots.txt, pausas, reintentos y topes
│   ├── listengine.py     Descubrimiento de eventos (listado paginado) y extracción de eventos y listas
│   ├── dom.py            Utilidades: clics robustos, búsqueda por texto y scroll
│   ├── listas.py         Parser de listas de ejército (facción, destacamentos, unidades, puntos, mejoras)
│   ├── normalizar.py     Convierte el JSON bruto en los CSV y anonimiza a los jugadores
│   └── diagnostico.py    Herramienta auxiliar: muestra qué ve el navegador en una página
└── dataset/              Dataset final en CSV
    ├── eventos.csv
    ├── participantes.csv
    └── unidades.csv
```

Los datos brutos (`source/salida/eventos_raw.json` y `.jsonl`) se generan al ejecutar el script, pero no se
versionan porque incluyen nombres de jugadores.

## 4. Cómo usar el código

### Requisitos
- Python 3.10 o superior (probado con 3.13).
- Google Chrome instalado. Selenium descarga el `chromedriver` adecuado automáticamente.

### Instalación (con entorno virtual)
```
python -m venv .venv
.venv\Scripts\activate       
pip install -r requirements.txt
```

### Configuración previa
En `source/config.py`, sustituye el correo de `USER_AGENT` por uno real (en mi caso usaremos el de la UOC). El scraper se identifica con ese
User-Agent (y comprueba al arrancar, con `navigator.userAgent`, que es el que realmente se envía).

### Parámetros de `main.py`
Todos son opcionales y sobrescriben los valores de `config.py`.

| Parámetro | Efecto | Por defecto |
|---|---|---|
| `--listar` | Muestra los eventos que pasan los filtros y termina, sin descargar nada | — |
| `--visible` | Muestra la ventana del navegador | sin ventana |
| `--max-eventos N` | Número máximo de eventos | 50 |
| `--desde AAAA-MM-DD` | Fecha mínima del evento | 2026-01-01 |
| `--hasta AAAA-MM-DD` | Fecha máxima del evento | sin límite |
| `--min-jugadores N` | Descarta eventos con menos de N jugadores | 0 |
| `--nombre REGEX` | Solo eventos cuyo nombre cumpla la expresión regular (sin distinguir mayúsculas) | todos |
| `--jugadores-web {+20,+50,+100}` | Usa el filtro *Number of Players* de la propia web | sin filtro |
| `--listas N` | Listas descargadas por evento, de los mejor clasificados (`0` = todas) | 10 |
| `--sin-normalizar` | No genera los CSV al terminar (solo el JSON bruto) | genera los CSV |

Otros scripts:

| Comando | Efecto |
|---|---|
| `python source/normalizar.py [--entrada JSON] [--dir CARPETA]` | Regenera los CSV desde el JSON bruto (por defecto `source/salida/eventos_raw.json` → `dataset/`) |
| `python source/diagnostico.py [URL]` | Muestra título, enlaces y texto visible de una página, y guarda una captura en `source/salida/` |

### Ejemplos replicables
Ejecutados desde la raíz del repositorio:

```
# 1) Ver qué eventos pasan los filtros, sin descargar nada
python source/main.py --listar --desde 2026-06-01

# 2) Prueba mínima: un evento y 3 listas, viendo el navegador
python source/main.py --max-eventos 1 --listas 3 --visible

# 3) Eventos grandes desde junio, con 20 listas por evento
python source/main.py --desde 2026-06-01 --min-jugadores 40 --listas 20

# 4) Solo torneos cuyo nombre incluya "GT" o "Grand Tournament"
python source/main.py --nombre "\bGT\b|Grand Tournament" --jugadores-web +50

# 5) Regenerar los CSV a partir de los datos brutos ya descargados
python source/normalizar.py
```

La ejecución se puede interrumpir y reanudar: `source/salida/eventos_raw.jsonl` guarda un evento por línea y los
eventos ya descargados no se repiten.

## 5. Contenido del dataset

Descripción completa de cada campo en la memoria (apartado 5). Resumen:

| Fichero | Una fila por… | Campos principales |
|---|---|---|
| `eventos.csv` | Evento | `evento_url`, `nombre`, `fecha`, `n_jugadores`, `participantes_leidos`, `listas_descargadas`, `listas_legibles` |
| `participantes.csv` | Participante en un evento | `evento_url`, `jugador_id` (seudonimizado), `posicion`, `faccion`, `destacamento`, `disposicion_fuerzas`, `victorias`, `derrotas`, `empates`, `puntos_total`, `n_unidades`, `mejoras`, `unidades`, `coherente` |
| `unidades.csv` | Unidad de una lista | `evento_url`, `jugador_id`, `faccion`, `destacamento`, `disposicion_fuerzas`, `unidad`, `puntos`, `seccion`, `mejora` |

Las tres tablas se relacionan por `evento_url` y `jugador_id`. Periodo cubierto: 01/01/2026 - 21/10/2026.

## 6. Cómo funciona

1. Abre `/events`, espera a que la aplicación muestre las tarjetas y acepta las cookies opcionales.
2. Recorre el listado pulsando *Next*, aplica los filtros y se detiene al salir del rango de fechas.
3. Entra en cada evento (`/events/<id>`) y lee las filas de todos los jugadores ejecutando JavaScript en el navegador.
4. Abre la página de lista (`/lists/<id>`) de los mejor clasificados y guarda su texto.
5. Guarda cada evento en JSONL, vuelca el JSON bruto y genera los CSV, seudonimizando a los jugadores.

## 7. Uso responsable y consideraciones éticas

- Se consulta `robots.txt` antes de cada URL y no se visita lo que no esté permitido (en este caso no tenemos un robots.txt)
- User-Agent propio con propósito y contacto, comprobado al arrancar.
- Pausas aleatorias de 3 a 6 s entre páginas, reintentos con espera exponencial y tope de 2.000 peticiones por ejecución.
- No se inicia sesión, no se resuelven captchas ni se eluden protecciones; las cookies opcionales se aceptan.
- Los nombres de jugador son datos personales: en los CSV se sustituyen por un hash (`config.ANONIMIZAR`) y los datos
  brutos no se publican.

## 8. Limitaciones

- Por defecto solo se descargan las listas de los 10 mejor clasificados de cada evento: los análisis por unidad se
  basan en esa muestra; los análisis por facción o destacamento usan a todos los participantes.
- El parser de listas está pensado para el formato que muestra ListEngine; el campo `coherente` marca las listas
  cuya suma de puntos no coincide con el total y que pueden estar mal interpretadas.
- La estructura de la web puede cambiar y obligar a ajustar los selectores de `listengine.py`.

## 9. Licencia

- Dataset: CC BY-NC-SA 4.0.
- Código:  Apache License 2.0.
- Fuente de los datos: ListEngine (https://www.listengine.online). Warhammer 40,000 es una marca de Games Workshop.