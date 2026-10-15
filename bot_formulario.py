import os
import subprocess
import time
import urllib.request
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://forms.cloud.microsoft/pages/responsepage.aspx?id=uvfTxJJ4nUy6BgKoT5oJle5LM_5RQbhEiwJCr2Dc7x5UNzJVQVgwTVFDREE3T0RLU1JZWVVXMUVUSS4u&origin=lprLink&route=shorturl"

# ¿Se está ejecutando en GitHub Actions?
EN_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"

# ---------- Modo de prueba: True = solo prueba la fecha (página 1) y se detiene ----------
SOLO_PROBAR_FECHA = True   # <-- ponlo en False cuando la fecha funcione

# ---------- Datos fijos (en GitHub se leen de los Secrets; en tu PC se usan estos valores) ----------
NOMBRE = os.environ.get("NOMBRE") or "JHON ALEXANDER RODRIGUEZ NIÑO"
CEDULA = os.environ.get("CEDULA") or "1005039272"
CIUDAD = os.environ.get("CIUDAD") or "CUCUTA"

PLACA = os.environ.get("PLACA") or "YCQ56G"
MARCA = os.environ.get("MARCA") or "PULSAR"
MODELO = os.environ.get("MODELO") or "2024"
CILINDRAJE = os.environ.get("CILINDRAJE") or "160"

# ---------- Kilometraje ----------
KM_INICIAL = int(os.environ.get("KM_INICIAL") or "15000")   # kilometraje REAL en FECHA_BASE
FECHA_BASE = datetime(2026, 10, 9)
KM_POR_DIA = 15

# ---------- Última página ----------
OBSERVACIONES = "SIN NOVEDAD"

# ---------- Ajustes del Bot ----------
CONFIRMAR_SALUD = False
CONFIRMAR_REVISION = False
APAGAR_PC_AL_TERMINAR = True   # solo aplica en tu PC con Windows; en GitHub se ignora

# ---------- Chrome del bot (solo para tu PC con Windows) ----------
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PERFIL_BOT = r"C:\bot_chrome_perfil_nuevo"
PUERTO = 9222


# ======================= FUNCIONES AUXILIARES =======================

def cerrar_chrome():
    """Cierra Chrome y chromedriver para evitar perfiles en uso (solo Windows)."""
    for proceso in ("chrome.exe", "chromedriver.exe"):
        subprocess.run(["taskkill", "/F", "/IM", proceso],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def limpiar_bloqueos():
    """Borra archivos que Chrome deja cuando se cierra mal."""
    for nombre in ("lockfile", "SingletonLock", "SingletonCookie",
                   "SingletonSocket", "DevToolsActivePort"):
        ruta = os.path.join(PERFIL_BOT, nombre)
        try:
            if os.path.exists(ruta):
                os.remove(ruta)
        except Exception:
            pass


def crear_driver():
    # ----- Modo servidor (GitHub Actions) -----
    if EN_GITHUB:
        opciones = webdriver.ChromeOptions()
        opciones.add_argument("--headless=new")
        opciones.add_argument("--no-sandbox")
        opciones.add_argument("--disable-dev-shm-usage")
        opciones.add_argument("--window-size=1366,900")
        opciones.add_argument("--lang=es-CO")
        opciones.add_experimental_option("prefs", {"intl.accept_languages": "es-CO,es"})
        return webdriver.Chrome(options=opciones)

    # ----- Modo Windows (tu PC) -----
    cerrar_chrome()
    os.makedirs(PERFIL_BOT, exist_ok=True)
    limpiar_bloqueos()

       subprocess.Popen([
        CHROME_EXE,
        f"--remote-debugging-port={PUERTO}",
        f"--user-data-dir={PERFIL_BOT}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
    ])
