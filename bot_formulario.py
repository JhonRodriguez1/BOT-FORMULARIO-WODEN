from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from datetime import datetime
import time
import os

URL = "https://forms.cloud.microsoft/pages/responsepage.aspx?id=uvfTxJJ4nUy6BgKoT5oJle5LM_5RQbhEiwJCr2Dc7x5UNzJVQVgwTVFDREE3T0RLU1JZWVVXMUVUSS4u&origin=lprLink&route=shorturl"

# ---------- Modo de prueba: True = solo prueba la fecha (página 1) y se detiene ----------
SOLO_PROBAR_FECHA = False

# ---------- Datos fijos del conductor ----------
NOMBRE = "JHON ALEXANDER RODRIGUEZ NIÑO"
CEDULA = "1005039272"
CIUDAD = "CUCUTA"

# ---------- Datos fijos de la moto  <-- CAMBIA ESTOS VALORES POR LOS REALES ----------
PLACA = "YCQ56G"
MARCA = "PULSAR"
MODELO = "2024"
CILINDRAJE = "160"

# ---------- Kilometraje: aumenta 15 km por día ----------
KM_INICIAL = 15000                      # <-- kilometraje REAL de tu moto en FECHA_BASE
FECHA_BASE = datetime(2026, 10, 9)
KM_POR_DIA = 15

# ---------- Última página ----------
OBSERVACIONES = "SIN NOVEDAD"

# ---------- Ajustes del Bot ----------
CONFIRMAR_SALUD = False
CONFIRMAR_REVISION = False
APAGAR_PC_AL_TERMINAR = True  # <-- Cambia a False si NO quieres que se apague solo

# ---------- Perfil de Chrome propio del bot (guarda tu sesión de Microsoft) ----------
PERFIL_BOT = r"C:\Users\Usuario\bot_chrome_perfil"


# ======================= FUNCIONES AUXILIARES =======================

def crear_driver():
    opciones = webdriver.ChromeOptions()
    opciones.add_argument(f"--user-data-dir={PERFIL_BOT}")
    opciones.add_argument("--start-maximized")
    opciones.add_argument("--no-first-run")
    opciones.add_argument("--no-default-browser-check")
    opciones.add_argument("--disable-features=ChromeWhatsNewUI")
    # opciones.add_argument("--headless=new")   # actívalo solo cuando todo funcione sin errores
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
    """Espera el campo de fecha. Si aparece el login, te da 3 minutos para iniciar sesión a mano."""
    xpath_fecha = "//input[starts-with(@id,'DatePicker')]"
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, xpath_fecha)))
    except TimeoutException:
        print("⚠️ No apareció el formulario. Si ves una pantalla de inicio de sesión,")
        print("   inicia sesión en el navegador ahora (tienes 3 minutos).")
        WebDriverWait(driver, 180).until(
            EC.presence_of_element_located((By.XPATH, xpath_fecha)))
        print("✅ Sesión iniciada. Continuando...")


def poner_fecha_hoy(driver, wait):
    """Pone la fecha de hoy asegurando el formato correcto (DD/MM/YYYY)."""
    xpath_campo = "//input[starts-with(@id,'DatePicker')]"
    campo = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_campo)))
    time.sleep(1) # Deja que los scripts de la página carguen

    # 1. Formato con ceros a la izquierda (ej. 09/10/2026).
    fecha_str = datetime.now().strftime("%d/%m/%Y")

    try:
        # 2. Hacer clic en el campo para enfocarlo
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", campo)
        campo.click()
        time.sleep(0.5)

        # 3. Borrar lo que haya (Windows/Linux usan Ctrl+A)
        campo.send_keys(Keys.CONTROL, "a")
        campo.send_keys(Keys.BACKSPACE)
        time.sleep(0.2)

        # 4. Escribir la fecha y presionar TAB para confirmar
        campo.send_keys(fecha_str)
        time.sleep(0.5)
        campo.send_keys(Keys.TAB)
        time.sleep(1)

        # 5. Verificamos si quedó escrita
        valor_actual = driver.execute_script("return arguments[0].value;", campo)
        if valor_actual:
            print(f"✅ Fecha puesta exitosamente: {valor_actual}")
            return
            
        # PLAN B: Si el teclado no funcionó, forzamos el valor directo en React
        print("Intentando forzar la fecha por JavaScript...")
        driver.execute_script("""
            let el = arguments[0];
            let val = arguments[1];
            let setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, val);
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
        """, campo, fecha_str)
        time.sleep(1)
        
    except Exception as e:
        raise Exception(f"No se pudo poner la fecha. Detalles: {e}")


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
            input("Modo prueba: mira el campo de fecha. Enter para cerrar...")
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
        if CONFIRMAR_SALUD:
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
        if CONFIRMAR_REVISION:
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

        # --- APAGADO AUTOMÁTICO DEL PC ---
        if APAGAR_PC_AL_TERMINAR:
            print("Apagando el equipo en 60 segundos... (presiona Windows + R y escribe 'shutdown /a' para cancelar)")
            os.system("shutdown /s /t 60")

    except Exception as e:
        print(f"❌ Error en la página {pagina}: {type(e).__name__}: {e}")
        try:
            print("URL actual:", driver.current_url)
            driver.save_screenshot("error.png")
            print("Captura guardada como error.png")
            input("Mira el navegador y presiona Enter para cerrar...")
        except Exception:
            print("El navegador ya se había cerrado.")
        finally:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    llenar_formulario_diario()
