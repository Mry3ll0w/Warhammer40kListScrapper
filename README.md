# Scraper de ListEngine (Warhammer 40K, 11ª edición)

Extrae de https://www.listengine.online eventos, participantes (facción, destacamento,
disposición de fuerzas, resultado W-L-D) y listas completas (unidades con puntos y mejoras).

## Instalación
```
python -m venv .venv
.venv\Scripts\activate        # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```
Cambia el correo de `USER_AGENT` en `config.py`.

## Uso
```
python main.py --listar                              # qué eventos pasan los filtros (no descarga nada)
python main.py --max-eventos 1 --visible             # prueba corta viendo el navegador
python main.py --desde 2026-06-01 --min-jugadores 40 --listas 20
python main.py --nombre "GT|Grand Tournament" --jugadores-web +50
python normalizar.py                                 # regenera los CSV desde el JSON bruto
```
La ejecución se puede cortar y reanudar: `salida/eventos_raw.jsonl` guarda un evento por línea.

## Salidas (`salida/`)
- `eventos_raw.json` datos brutos (incluye nombres de jugadores: no publicar tal cual)
- `participantes.csv` / `participantes.json` una fila por participante
- `unidades.csv` una fila por unidad de cada lista
- `eventos.csv` una fila por evento

## Arquitectura
| Módulo | Función |
|---|---|
| `navegador.py` | Selenium con User-Agent propio (se comprueba), robots.txt, pausas aleatorias, reintentos y tope |
| `listengine.py` | Descubrimiento (listado paginado + filtros), eventos y listas |
| `dom.py` | Clics robustos, búsqueda por texto y scroll |
| `listas.py` | Parser de listas de ejército |
| `normalizar.py` | JSON bruto -> CSV (anonimiza jugadores) |
| `diagnostico.py` | Muestra qué ve el navegador en una página |

## Aspectos éticos y legales
- Solo se accede a páginas públicas, con pausas de 3-6 s y tope de peticiones.
- No se usa ninguna API ni se sortea ninguna restricción.
- Los nombres de jugador son datos personales: el dataset los sustituye por un hash.
