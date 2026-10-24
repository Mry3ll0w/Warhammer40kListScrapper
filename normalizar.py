"""
Convierte el JSON bruto en datasets tabulares.

    python normalizar.py                          # usa salida/eventos_raw.json
    python normalizar.py --entrada otro.json --dir otra_carpeta

Genera en la carpeta de salida:
  participantes.json  estructura completa (unidades y mejoras anidadas)
  participantes.csv   una fila por participante: evento, puesto, facción, destacamento(s),
                      disposición de fuerzas, W-L-D, lista (unidades con puntos, mejoras)
  unidades.csv        formato largo: una fila por unidad de cada lista (útil para analizar)
  eventos.csv         una fila por evento

Privacidad: con config.ANONIMIZAR el nombre del jugador no se guarda (solo un hash).
"""
import argparse
import csv
import hashlib
import json
import os

import config
from listas import norm, parsear_lista


def id_jugador(nombre, url_evento):
    return hashlib.sha1(f"{url_evento}|{norm(nombre)}".encode("utf-8")).hexdigest()[:10]


def procesar(eventos):
    tabla_eventos, participantes, unidades = [], [], []
    for ev in eventos:
        if "error" in ev:
            continue
        listas = {norm(i["jugador"]): i for i in ev.get("listas_brutas", [])}
        n_legibles = 0
        for p in ev.get("participantes", []):
            item = listas.get(norm(p["jugador"]))
            lista = parsear_lista(item["texto"]) if item else None
            pid = id_jugador(p["jugador"], ev["url"])
            fila = {
                "evento_url": ev["url"], "evento_nombre": ev.get("nombre") or ev.get("titulo_pagina"),
                "evento_fecha": ev.get("fecha"), "evento_n_jugadores": ev.get("n_jugadores"),
                "jugador_id": pid, "posicion": p.get("posicion"),
                "faccion": p.get("faccion"), "destacamento": p.get("destacamento"),
                "destacamentos": p.get("destacamentos"), "disposicion_fuerzas": p.get("disposicion_fuerzas"),
                "victorias": p.get("victorias"), "derrotas": p.get("derrotas"), "empates": p.get("empates"),
                "lista_url": p.get("lista_url"),
                "lista_descargada": item is not None, "lista_disponible": lista is not None,
                "posible_contenido_restringido": (item or {}).get("posible_contenido_restringido", False),
            }
            if not config.ANONIMIZAR:
                fila["jugador"] = p["jugador"]
            if lista:
                n_legibles += 1
                for k in ("nombre_lista", "tamano_batalla", "puntos_total", "n_unidades",
                          "puntos_suma_unidades", "coherente", "mejoras", "unidades"):
                    fila[k] = lista[k]
                for u in lista["unidades"]:
                    unidades.append({
                        "evento_url": ev["url"], "jugador_id": pid, "posicion": fila["posicion"],
                        "faccion": fila["faccion"], "destacamento": fila["destacamento"],
                        "disposicion_fuerzas": fila["disposicion_fuerzas"],
                        "unidad": u["nombre"], "puntos": u["puntos"],
                        "seccion": u["seccion"], "mejora": u["mejora"]})
            participantes.append(fila)
        tabla_eventos.append({
            "evento_url": ev["url"], "nombre": ev.get("nombre"), "fecha": ev.get("fecha"),
            "n_jugadores": ev.get("n_jugadores"), "participantes_leidos": len(ev.get("participantes", [])),
            "listas_descargadas": len(listas), "listas_legibles": n_legibles})
    return tabla_eventos, participantes, unidades


def _plano(p):
    q = {k: v for k, v in p.items() if k not in ("mejoras", "unidades", "destacamentos")}
    q["mejoras"] = "; ".join(f"{m['nombre']} (+{m['puntos']})" for m in p.get("mejoras", []))
    q["unidades"] = "; ".join(f"{u['nombre']} ({u['puntos']})" for u in p.get("unidades", []))
    q["unidades_json"] = json.dumps(p.get("unidades", []), ensure_ascii=False)
    return q


def _csv(ruta, filas):
    if not filas:
        return
    cols = list(dict.fromkeys(k for fila in filas for k in fila))
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)


def generar(ruta_json, carpeta):
    with open(ruta_json, encoding="utf-8") as f:
        eventos = json.load(f)
    tabla_eventos, participantes, unidades = procesar(eventos)
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "participantes.json"), "w", encoding="utf-8") as f:
        json.dump(participantes, f, ensure_ascii=False, indent=2)
    _csv(os.path.join(carpeta, "participantes.csv"), [_plano(p) for p in participantes])
    _csv(os.path.join(carpeta, "unidades.csv"), unidades)
    _csv(os.path.join(carpeta, "eventos.csv"), tabla_eventos)
    con_lista = sum(p["lista_disponible"] for p in participantes)
    print(f"Eventos: {len(tabla_eventos)} | participantes: {len(participantes)} | "
          f"con lista legible: {con_lista} | unidades: {len(unidades)} | salida en {carpeta}/")
    descargadas = sum(p["lista_descargada"] for p in participantes)
    if descargadas and not con_lista:
        print("Hay listas descargadas pero ninguna se pudo leer: revisa el formato en el JSON bruto (campo 'texto').")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default=config.SALIDA_JSON)
    ap.add_argument("--dir", default=config.DIR_SALIDA)
    args = ap.parse_args()
    generar(args.entrada, args.dir)


if __name__ == "__main__":
    main()
