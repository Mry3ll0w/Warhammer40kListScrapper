"""
Punto de entrada: descubre eventos en ListEngine, descarga participantes y listas,
guarda JSON bruto y genera los datasets tabulares.

    python main.py --listar                       # solo muestra qué eventos pasan los filtros
    python main.py --max-eventos 1 --visible      # prueba corta viendo el navegador
    python main.py --desde 2026-06-01 --min-jugadores 40 --listas 20
    python main.py --nombre "GT|Grand Tournament" --jugadores-web +50
"""
import argparse
import json
import os

import config
from listengine import descubrir_eventos, extraer_evento
from navegador import Navegador, TopeAlcanzado
from normalizar import generar


def urls_ya_procesadas(ruta):
    """Permite reanudar: lee el JSONL previo y devuelve las URLs ya guardadas."""
    if not os.path.exists(ruta):
        return set()
    with open(ruta, encoding="utf-8") as f:
        return {json.loads(l)["url"] for l in f if l.strip()}


def volcar_json(ruta_jsonl, ruta_json):
    with open(ruta_jsonl, encoding="utf-8") as f:
        datos = [json.loads(l) for l in f if l.strip()]
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"Volcado final: {len(datos)} eventos en {ruta_json}")


def leer_argumentos():
    ap = argparse.ArgumentParser(description="Scraper de ListEngine (eventos, participantes y listas)")
    ap.add_argument("--listar", action="store_true", help="solo lista los eventos que pasan los filtros")
    ap.add_argument("--visible", action="store_true", help="muestra el navegador")
    ap.add_argument("--max-eventos", type=int)
    ap.add_argument("--desde", help="fecha mínima AAAA-MM-DD")
    ap.add_argument("--hasta", help="fecha máxima AAAA-MM-DD")
    ap.add_argument("--min-jugadores", type=int)
    ap.add_argument("--nombre", help="regex sobre el nombre del evento")
    ap.add_argument("--jugadores-web", choices=["+20", "+50", "+100"], help="filtro 'Number of Players' de la web")
    ap.add_argument("--listas", type=int, help="listas por evento (0 = todas)")
    ap.add_argument("--sin-normalizar", action="store_true")
    a = ap.parse_args()
    # Los argumentos sobrescriben config.py
    if a.visible:
        config.HEADLESS = False
    if a.max_eventos is not None:
        config.MAX_EVENTOS = a.max_eventos
    if a.desde:
        config.FECHA_MIN = a.desde
    if a.hasta:
        config.FECHA_MAX = a.hasta
    if a.min_jugadores is not None:
        config.MIN_JUGADORES = a.min_jugadores
    if a.nombre:
        config.FILTRO_NOMBRE = a.nombre
    if a.jugadores_web:
        config.FILTRO_JUGADORES_WEB = a.jugadores_web
    if a.listas is not None:
        config.MAX_LISTAS_POR_EVENTO = a.listas or None
    return a


def main():
    args = leer_argumentos()
    os.makedirs(config.DIR_SALIDA, exist_ok=True)
    nav = Navegador()
    try:
        eventos = descubrir_eventos(nav)
        print(f"\nEventos tras filtros: {len(eventos)}")
        if args.listar:
            for _, resumen in eventos:
                print("  ", resumen)
            return
        hechos = urls_ya_procesadas(config.SALIDA_JSONL)
        with open(config.SALIDA_JSONL, "a", encoding="utf-8") as salida:
            for i, (url, resumen) in enumerate(eventos, 1):
                if url in hechos:
                    continue
                print(f"[{i}/{len(eventos)}] {resumen}")
                try:
                    registro = extraer_evento(nav, url, resumen)
                except TopeAlcanzado as e:
                    print(e)
                    break
                except Exception as e:  # un evento fallido no tumba toda la ejecución
                    print(f"   Error: {e}")
                    registro = {"url": url, "error": str(e)}
                salida.write(json.dumps(registro, ensure_ascii=False) + "\n")
                salida.flush()  # guardado incremental
    finally:
        nav.cerrar()
    volcar_json(config.SALIDA_JSONL, config.SALIDA_JSON)
    if not args.sin_normalizar:
        generar(config.SALIDA_JSON, config.DIR_SALIDA)


if __name__ == "__main__":
    main()
