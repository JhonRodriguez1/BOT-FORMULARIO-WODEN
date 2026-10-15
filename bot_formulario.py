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

# ---------- Modo de prueba: True = solo prueba la fecha (página 1) y NO envía ----------
SOLO_PROBAR_FECHA = False

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
    """Cierra Chrome y chromedriver (solo Windows)."""
    if os.name != "nt":
        return
    for proceso in ("chrome.exe", "chromedriver.exe"):
        subprocess.run(["taskkill", "/F", "/IM", proceso],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def limpiar_bloqueos():
    """Borra archivos que Chrome deja cuando se cierra mal (solo Windows)."""
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

    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json/version", timeout=1)
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("Chrome no abrió. Revisa la ruta de CHROME_EXE o el antivirus.")

    opciones = webdriver.ChromeOptions()
    opciones.debugger_address = f"127.0.0.1:{PUERTO}"
    return webdriver.Chrome(options=opciones)


def texto_de_pregunta(wait, titulo):
    xpath = (f"//div[@data-automation-id='questionItem']"
             f"[.//span[@data-automation-id='questionTitle'][contains(., '{titulo}')]]"
             f"//input[@data-automation-id='textInput']")
    return wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))


def click_js(driver, elemento):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elemento)
    driver.execute_script("arguments[0].click();", elemento)


def click_siguiente(driver, wait):
    boton = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//button[@data-automation-id='nextButton']")))
    click_js(driver, boton)


def kilometraje_de_hoy():
    dias = (datetime.now().date() - FECHA_BASE.date()).days
    return str(KM_INICIAL + KM_POR_DIA * max(dias, 0))


def marcar_todo_bueno(driver):
    """Marca 'Bueno' en todas las filas Likert (el aria-label termina en 'Bueno')."""
    xpath = ("//input[@type='radio' and "
             "substring(normalize-space(@aria-label), "
             "string-length(normalize-space(@aria-label)) - 4)='Bueno']")
    opciones = driver.find_elements(By.XPATH, xpath)
    for op in opciones:
        click_js(driver, op)
        time.sleep(0.15)
    return len(opciones)


def esperar_formulario(driver):
    """Espera el campo de fecha. En tu PC, si aparece el login, te da 3 minutos para iniciar sesión."""
    xpath_fecha = "//input[starts-with(@id,'DatePicker')]"
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, xpath_fecha)))
    except TimeoutException:
        if EN_GITHUB:
            raise RuntimeError("El formulario no cargó (¿pide inicio de sesión de Microsoft?).")
        print("⚠️ No apareció el formulario. Si ves una pantalla de inicio de sesión,")
        print("   inicia sesión en el navegador ahora (tienes 3 minutos).")
        WebDriverWait(driver, 180).until(
            EC.presence_of_element_located((By.XPATH, xpath_fecha)))
        print("✅ Sesión iniciada. Continuando...")


def poner_fecha_hoy(driver, wait):
    """Pone la fecha de hoy. En GitHub usa el calendario primero; en tu PC, el teclado primero."""
    xpath_campo = "//input[starts-with(@id,'DatePicker')]"
    wait.until(EC.element_to_be_clickable((By.XPATH, xpath_campo)))
    time.sleep(2)

    hoy = datetime.now()
    # El campo pide d/MM/yyyy (ej. 4/10/2026 o 14/10/2026)
    formatos = [f"{hoy.day}/{hoy.month:02d}/{hoy.year}",
                hoy.strftime("%d/%m/%Y"),
                f"{hoy.month}/{hoy.day}/{hoy.year}",
                hoy.strftime("%m/%d/%Y")]

    info = driver.execute_script(
        "var e=document.querySelector(\"input[id^='DatePicker']\");"
        "return e ? [e.placeholder||'', e.getAttribute('aria-label')||''] : ['',''];")
    print("Placeholder / aria-label del campo:", info)

    def valor():
        return (driver.execute_script(
            "var e=document.querySelector(\"input[id^='DatePicker']\");"
            "return e ? e.value : '';") or "").strip()

    def hay_error():
        return driver.execute_script(
            "return document.querySelectorAll(\"[role='alert']\").length;") > 0

    def por_calendario():
        campo = driver.find_element(By.XPATH, xpath_campo)
        click_js(driver, campo)
        time.sleep(1.5)
        ok = driver.execute_script("""
            const btn = document.querySelector("button[class*='dayIsToday']");
            if (btn) { btn.click(); return true; }
            return false;
        """)
        time.sleep(1)
        if ok and valor():
            print("✅ Fecha puesta desde el calendario:", valor())
            return True
        return False

    def por_teclado():
        for texto in formatos:
            campo = driver.find_element(By.XPATH, xpath_campo)
            click_js(driver, campo)
            campo.send_keys(Keys.CONTROL, "a")
            campo.send_keys(Keys.DELETE)
            for ch in texto:
                campo.send_keys(ch)
                time.sleep(0.1)
            campo.send_keys(Keys.TAB)
            time.sleep(1)
            if valor() and not hay_error():
                print(f"✅ Fecha puesta con formato '{texto}': {valor()}")
                return True
            print(f"El campo rechazó '{texto}', pruebo otro formato...")
        return False

    metodos = [por_calendario, por_teclado] if EN_GITHUB else [por_teclado, por_calendario]
    for metodo in metodos:
        if metodo():
            return

    raise Exception("No se pudo poner la fecha")


# ======================= PROCESO PRINCIPAL =======================

def llenar_formulario_diario():
    driver = crear_driver()
    pagina = "inicio"

    try:
        driver.get(URL)
        esperar_formulario(driver)
        wait = WebDriverWait(driver, 20)

        # ---------- PÁGINA 1: Fecha automática ----------
        pagina = "1 (Fecha)"
        print("Página 1...")
        poner_fecha_hoy(driver, wait)

        if SOLO_PROBAR_FECHA:
            print("Modo prueba: la fecha quedó puesta, no se envió nada.")
            if not EN_GITHUB:
                input("Mira el campo de fecha. Enter para cerrar...")
            driver.quit()
            return

        time.sleep(1)
        click_siguiente(driver, wait)

        # ---------- PÁGINA 2: Datos del Conductor ----------
        pagina = "2 (Datos del conductor)"
        print("Página 2...")
        texto_de_pregunta(wait, "Nombres y Apellidos").send_keys(NOMBRE)
        texto_de_pregunta(wait, "Documento de Identidad").send_keys(CEDULA)
        texto_de_pregunta(wait, "Ciudad").send_keys(CIUDAD)
        time.sleep(1)
        click_siguiente(driver, wait)

        # ---------- PÁGINA 3: Condiciones de salud ----------
        pagina = "3 (Salud)"
        print("Página 3...")
        if CONFIRMAR_SALUD and not EN_GITHUB:
            resp = input("¿Confirmas que estás en condiciones óptimas para conducir? (s/n): ")
            if resp.strip().lower() != "s":
                print("⛔ No se envió el formulario.")
                driver.quit()
                return

        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='radio' and @value='Si']")))

        # Pregunta 5: "No" (value='2') en las 5 filas
        filas_no = driver.find_elements(
            By.XPATH, "//input[@type='radio' and @data-row-id and @value='2']")
        for op in filas_no:
            click_js(driver, op)
            time.sleep(0.3)
        print(f"Pregunta 5: {len(filas_no)} respuestas 'No' marcadas (esperadas: 5)")

        # Pregunta 6: "Si"
        op_si = driver.find_element(
            By.XPATH,
            "//div[@data-automation-id='questionItem']"
            "[.//span[@data-automation-id='questionTitle'][contains(., 'condiciones')]]"
            "//input[@type='radio' and @value='Si']")
        click_js(driver, op_si)
        time.sleep(1)
        click_siguiente(driver, wait)

        # ---------- PÁGINA 4: Información del Vehículo ----------
        pagina = "4 (Vehículo)"
        print("Página 4...")
        texto_de_pregunta(wait, "Placa").send_keys(PLACA)
        texto_de_pregunta(wait, "Marca").send_keys(MARCA)
        texto_de_pregunta(wait, "Modelo").send_keys(MODELO)
        texto_de_pregunta(wait, "Cilindraje").send_keys(CILINDRAJE)
        time.sleep(1)
        click_siguiente(driver, wait)

        # ---------- PÁGINA 5: Revisión de la moto ----------
        pagina = "5 (Revisión)"
        print("Página 5...")
        if CONFIRMAR_REVISION and not EN_GITHUB:
            resp = input("¿Revisaste la moto y todo está BUENO? (s/n): ")
            if resp.strip().lower() != "s":
                print("⛔ No se envió el formulario.")
                driver.quit()
                return

        # Pregunta 11: documentos vigentes -> "Si"
        op_si = wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//div[@data-automation-id='questionItem']"
            "[.//span[@data-automation-id='questionTitle'][contains(., 'tarjeta de propiedad')]]"
            "//input[@type='radio' and @value='Si']")))
        click_js(driver, op_si)

        # Pregunta 12: kilometraje
        km = kilometraje_de_hoy()
        texto_de_pregunta(wait, "Kilometraje").send_keys(km)
        print(f"Kilometraje registrado: {km}")

        # Preguntas 13 a 18: todo "Bueno"
        marcadas = marcar_todo_bueno(driver)
        print(f"Opciones 'Bueno' marcadas: {marcadas} (esperadas: 46)")
        time.sleep(1)
        click_siguiente(driver, wait)

        # ---------- PÁGINA 6: Observaciones y Enviar ----------
        pagina = "6 (Observaciones / Enviar)"
        print("Página 6...")
        texto_de_pregunta(wait, "Observaciones").send_keys(OBSERVACIONES)
        time.sleep(1)

        boton_enviar = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//button[@data-automation-id='submitButton']")))
        click_js(driver, boton_enviar)

        time.sleep(4)
        print("✅ Formulario enviado.")
        driver.quit()

        # --- APAGADO AUTOMÁTICO DEL PC (solo en tu PC, nunca en GitHub) ---
        if APAGAR_PC_AL_TERMINAR and not EN_GITHUB:
            print("Apagando el equipo en 60 segundos... (Windows + R y escribe 'shutdown /a' para cancelar)")
            os.system("shutdown /s /t 60")

    except Exception as e:
        print(f"❌ Error en la página {pagina}: {type(e).__name__}: {e}")
        try:
            print("URL actual:", driver.current_url)
            driver.save_screenshot("error.png")
            print("Captura guardada como error.png")
            print("Texto visible:", driver.find_element(By.TAG_NAME, "body").text[:800])
            if not EN_GITHUB:
                input("Mira el navegador y presiona Enter para cerrar...")
        except Exception:
            print("El navegador ya se había cerrado.")
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        raise SystemExit(1)   # GitHub marca la ejecución como fallida


if __name__ == "__main__":
    llenar_formulario_diario()
