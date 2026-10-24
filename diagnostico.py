"""
Diagnóstico: muestra qué ve realmente Selenium en una página.

    python diagnostico.py                                      # /events
    python diagnostico.py https://www.listengine.online/events/<id>
    python diagnostico.py https://www.listengine.online/lists/<id>

Imprime título, enlaces y texto visible, y guarda salida/diag.png y salida/diag.html.
Usa el mismo Navegador responsable (User-Agent, robots.txt, pausas).
"""
import sys
import time
from collections import Counter
from urllib.parse import urlparse

from selenium.webdriver.common.by import By

import config
from navegador import Navegador

JS_RESUMEN = r"""
const a = [...document.querySelectorAll('a[href]')];
return {
  anclas: a.length,
  botones: [...document.querySelectorAll('button')].map(b => b.innerText.trim()).filter(Boolean).slice(0, 30),
  muestras: a.slice(0, 40).map(x => ({t: x.innerText.trim().replace(/\n/g, ' | ').slice(0, 60), h: x.href})),
  hrefs: a.map(x => x.href),
};
"""


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else config.URL_EVENTOS
    nav = Navegador()
    try:
        print(f"robots.txt permite {url}: {nav.robots.permitido(url)}")
        nav.abrir(url)
        time.sleep(5)  # margen para que la app pinte el contenido
        d = nav.driver
        print("URL final:", d.current_url, "\nTítulo   :", d.title)
        r = d.execute_script(JS_RESUMEN)
        print(f"\nEnlaces <a href>: {r['anclas']}\nBotones: {r['botones']}")
        print("\nPrimeros enlaces (texto -> destino):")
        for m in r["muestras"]:
            print(f"   {m['t']!r:62} -> {m['h']}")
        print("\nRutas más frecuentes:")
        for ruta, n in Counter("/" + urlparse(h).path.strip("/").split("/")[0] for h in r["hrefs"]).most_common(8):
            print(f"   {n:4d}  {ruta}")
        texto = d.find_element(By.TAG_NAME, "body").text
        print(f"\nTexto visible ({len(texto)} caracteres). Primeros 1500:\n{texto[:1500]!r}")
        d.save_screenshot(f"{config.DIR_SALIDA}/diag.png")
        with open(f"{config.DIR_SALIDA}/diag.html", "w", encoding="utf-8") as f:
            f.write(d.page_source)
        print(f"\nGuardados: {config.DIR_SALIDA}/diag.png y diag.html")
    finally:
        nav.cerrar()


if __name__ == "__main__":
    main()
