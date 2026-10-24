"""
Navegación responsable con Selenium: driver, comprobación del User-Agent,
respeto de robots.txt, pausas aleatorias, reintentos y tope de peticiones.
"""
import random
import time
from urllib.robotparser import RobotFileParser

import requests
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

import config


class TopeAlcanzado(RuntimeError):
    """Se alcanzó MAX_PETICIONES: se detiene la ejecución de forma ordenada."""


class RobotsGuard:
    """Descarga robots.txt (con nuestro User-Agent) y responde si una URL es rastreable."""

    def __init__(self, url_base, user_agent):
        self.ua = user_agent
        r = requests.get(url_base.rstrip("/") + "/robots.txt",
                         headers={"User-Agent": user_agent}, timeout=15)
        self.rp = RobotFileParser()
        if r.status_code == 200:
            self.rp.parse(r.text.splitlines())
        elif r.status_code == 404:
            self.rp.parse([])  # sin robots.txt: no hay restricciones declaradas
        else:
            # Ante la duda no se rastrea: puede ser un bloqueo
            raise RuntimeError(f"robots.txt devolvió {r.status_code}; no se continúa.")
        self.retardo = self.rp.crawl_delay(user_agent) or 0  # Crawl-delay si existe

    def permitido(self, url):
        return self.rp.can_fetch(self.ua, url)


class Navegador:
    """Envuelve el WebDriver añadiendo las medidas de uso responsable."""

    def __init__(self):
        self.driver = self._crear_driver()
        self.ua = self._comprobar_user_agent()
        self.robots = RobotsGuard(config.URL_BASE, config.USER_AGENT)
        self.peticiones = 0
        self._ultima = 0.0

    @staticmethod
    def _crear_driver():
        opts = Options()
        if config.HEADLESS:
            opts.add_argument("--headless=new")
        # Sin esto, el Chrome headless se anuncia como "HeadlessChrome"
        opts.add_argument(f"--user-agent={config.USER_AGENT}")
        opts.add_argument(f"--lang={config.IDIOMA}")
        opts.add_argument("--window-size=1366,900")
        driver = webdriver.Chrome(options=opts)  # Selenium Manager gestiona el chromedriver
        driver.set_page_load_timeout(45)
        return driver

    def _comprobar_user_agent(self):
        """Requisito de la práctica: verificar el UA real que ve el servidor."""
        ua = self.driver.execute_script("return navigator.userAgent;")
        print(f"[UA] User-Agent en uso: {ua}")
        if config.USER_AGENT not in ua:
            raise RuntimeError("El navegador no está usando el User-Agent configurado.")
        return ua

    def pausa(self):
        """Espera aleatoria entre acciones para no saturar el servidor."""
        espera = max(random.uniform(config.PAUSA_MIN, config.PAUSA_MAX), self.robots.retardo)
        restante = espera - (time.time() - self._ultima)
        if restante > 0:
            time.sleep(restante)
        self._ultima = time.time()

    def esperar_carga(self, timeout=20):
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete")

    def abrir(self, url):
        """Abre una URL comprobando robots.txt, tope y reintentos con espera exponencial."""
        if not self.robots.permitido(url):
            raise PermissionError(f"robots.txt no permite rastrear {url}")
        for intento in range(1, config.REINTENTOS + 1):
            if self.peticiones >= config.MAX_PETICIONES:
                raise TopeAlcanzado("Tope de peticiones alcanzado")
            self.pausa()
            try:
                self.driver.get(url)
                self.peticiones += 1
                self.esperar_carga()
                return
            except WebDriverException as e:
                print(f"   [reintento {intento}] {url}: {type(e).__name__}")
                time.sleep(2 ** intento)
        raise RuntimeError(f"No se pudo cargar {url}")

    def cerrar(self):
        self.driver.quit()
