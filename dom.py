"""Utilidades de interacción con el DOM: clics robustos, búsqueda por texto y scroll."""
import time

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

_MAY = "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ"
_MIN = "abcdefghijklmnopqrstuvwxyzáéíóú"


def clic(driver, el):
    """Clic real; si algo lo tapa (banners, overlays), se simula con JavaScript."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        el.click()
    except WebDriverException:
        driver.execute_script("arguments[0].click();", el)


def buscar_por_texto(driver, texto, exacto=False):
    """Primer botón/enlace/pestaña visible cuyo texto coincide (sin distinguir mayúsculas)."""
    norm = f"translate(normalize-space(.), '{_MAY}', '{_MIN}')"
    cond = f"{norm}='{texto.lower()}'" if exacto else f"contains({norm}, '{texto.lower()}')"
    xpath = f"//*[self::button or self::a or @role='tab'][{cond}]"
    for el in driver.find_elements(By.XPATH, xpath):
        if el.is_displayed():
            return el
    return None


def scroll_final(driver, rondas=5):
    """Baja la página para forzar la carga perezosa; se detiene si la altura ya no crece."""
    estable, altura_prev = 0, -1
    for _ in range(rondas):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.8)
        altura = driver.execute_script("return document.body.scrollHeight;")
        estable = estable + 1 if altura == altura_prev else 0
        if estable >= 2:
            break
        altura_prev = altura
