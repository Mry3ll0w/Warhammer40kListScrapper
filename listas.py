"""
Parser de listas de ejército de Warhammer 40,000 (texto plano).

Devuelve: facción, destacamento(s), disposición de fuerzas, tamaño de batalla,
mejoras y unidades con su coste en puntos.

IMPORTANTE - supuestos NO verificados sobre la 11ª edición:
  * Una lista puede llevar VARIOS destacamentos.
  * Además aparece un valor de "disposición de fuerzas" que, a juzgar por lo que
    muestran BCP y los agregadores, es uno de DISPOSICIONES (Take and Hold...).
    Confírmalo y amplía el conjunto si hay más valores.
  * La cabecera se detecta por la línea de la facción (conjunto FACCIONES) y se
    clasifica cada línea siguiente, así que no depende del orden exacto.
Si el formato real difiere, ajusta las constantes de arriba del todo.

Formato de ejemplo admitido:

    Mi lista (2000 Points)
    Necrons                      <- facción
    Cursed Legion                <- destacamento
    Skyshroud Spearhead          <- 2º destacamento (opcional)
    Purge the Foe                <- disposición de fuerzas
    Strike Force (2000 Points)   <- tamaño de batalla (opcional)

    CHARACTERS                   <- sección
    Overlord (85 Points)         <- unidad + coste
    • Enhancement: Nanoscarab Casket (+10 pts)   <- mejora
"""
import re

# Facciones (la lista coincide con las que publica Listhammer para 11ª)
FACCIONES = {f.lower() for f in [
    "Adepta Sororitas", "Adeptus Custodes", "Adeptus Mechanicus", "Aeldari", "Astra Militarum",
    "Black Templars", "Blood Angels", "Chaos Daemons", "Chaos Knights", "Chaos Space Marines",
    "Dark Angels", "Death Guard", "Deathwatch", "Drukhari", "Emperor's Children",
    "Genestealer Cult", "Grey Knights", "Imperial Agents", "Imperial Knights",
    "Leagues of Votann", "Necrons", "Orks", "Space Marines", "Space Marines (Astartes)",
    "Space Wolves", "T'au Empire", "Thousand Sons", "Tyranids", "World Eaters"]}
FACCIONES |= {f.replace("'", "") for f in FACCIONES}   # ListEngine las escribe sin apóstrofes
# Disposiciones de fuerzas vistas en BCP / agregadores (VERIFICAR si hay más)
DISPOSICIONES = {"take and hold", "reconnaissance", "priority assets", "purge the foe", "disruption"}
TAMANOS = ("combat patrol", "incursion", "strike force", "onslaught")

PTS = r"(?:points?|pts?|puntos?)"
RE_UNIDAD = re.compile(rf"^(?P<n>[^•·\-\*◦–+\s].*?)\s*\(\s*(?P<p>\d+)\s*{PTS}\s*\)\s*$", re.I)
RE_MEJORA = re.compile(rf"^\W*(?:enhancements?|mejoras?)\s*:\s*(?P<n>.+?)\s*\(\s*\+?\s*(?P<p>\d+)\s*{PTS}\s*\)\s*$", re.I)
FIN = re.compile(r"^(exported with|created with|exportado con)", re.I)


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def es_seccion(linea):
    """Cabeceras de sección: mayúsculas sin cifras (CHARACTERS, BATTLELINE...)."""
    return linea.isupper() and not re.search(r"\d", linea) and len(linea) < 45


def _es_unidad(linea):
    m = RE_UNIDAD.match(linea)
    return m if (m and norm(m["n"]) not in TAMANOS) else None


def _leer_cabecera(lineas):
    """Localiza la facción y clasifica las líneas de cabecera.

    Devuelve dict con faccion, destacamentos, disposicion, tamano, nombre_lista,
    total e 'inicio' (índice donde empiezan las unidades), o None.
    """
    i_fac = next((i for i, l in enumerate(lineas) if norm(l) in FACCIONES), None)
    if i_fac is None:
        return None
    cab = {"faccion": lineas[i_fac], "destacamentos": [], "disposicion": None,
           "tamano": None, "nombre_lista": None, "total": None}
    # Nombre de la lista y total: línea "Nombre (2000 Points)" justo antes de la facción
    for l in reversed([x for x in lineas[max(0, i_fac - 4):i_fac] if x]):
        m = RE_UNIDAD.match(l)
        if m and norm(m["n"]) not in TAMANOS:
            cab["nombre_lista"], cab["total"] = m["n"].strip(), int(m["p"])
            break
    j, vistas = i_fac + 1, 0
    while j < len(lineas) and vistas < 8:
        l = lineas[j]
        if not l:
            j += 1
            continue
        if es_seccion(l) or _es_unidad(l) or FIN.match(l):
            break
        m = RE_UNIDAD.match(l)
        if m and norm(m["n"]) in TAMANOS:          # "Strike Force (2000 Points)"
            cab["tamano"] = m["n"].strip()
            cab["total"] = cab["total"] or int(m["p"])
        elif norm(l) in DISPOSICIONES:
            cab["disposicion"] = l
        else:
            cab["destacamentos"].append(l)
        vistas += 1
        j += 1
    cab["inicio"] = j
    return cab


def parsear_lista(texto):
    """Texto -> dict con facción, destacamentos, disposición, mejoras y unidades."""
    lineas = [l.strip() for l in texto.replace("\r", "").split("\n")]
    cab = _leer_cabecera(lineas)
    if cab is None:
        return None

    unidades, mejoras, seccion = [], [], None
    for linea in lineas[cab["inicio"]:]:
        if not linea:
            continue
        if FIN.match(linea):
            break
        mej = RE_MEJORA.match(linea)
        if mej:  # la mejora se asocia a la última unidad leída
            unidad = unidades[-1]["nombre"] if unidades else None
            mejoras.append({"nombre": mej["n"].strip(), "puntos": int(mej["p"]), "unidad": unidad})
            if unidades:
                unidades[-1]["mejora"] = mej["n"].strip()
            continue
        if es_seccion(linea):
            seccion = linea.title()
            continue
        u = _es_unidad(linea)
        if u:
            unidades.append({"nombre": u["n"].strip(), "puntos": int(u["p"]),
                             "seccion": seccion, "mejora": None})
    suma = sum(u["puntos"] for u in unidades)
    return {
        "nombre_lista": cab["nombre_lista"],
        "faccion": cab["faccion"],
        "destacamentos": cab["destacamentos"],
        "destacamento": " + ".join(cab["destacamentos"]) or None,
        "disposicion_fuerzas": cab["disposicion"],
        "tamano_batalla": cab["tamano"],
        "puntos_total": cab["total"],
        "n_unidades": len(unidades),
        "puntos_suma_unidades": suma,
        "coherente": suma == cab["total"],   # detecta listas mal leídas
        "mejoras": mejoras,
        "unidades": unidades,
    }
