# core/pages/mercado_valores_page.py
import time
import random
from typing import Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from core.utils.log import log
from core.human import human_type, human_click_element

MERCADO_VALORES_URL = "https://appscvsgen.supercias.gob.ec/consultaCompanias/mercadoValores/busquedaEntesMv.jsf"

def _sleep(a: float, b: float):
    time.sleep(random.uniform(a, b))

# --------------------
# Finders del formulario
# --------------------
def find_main_input(driver, timeout: int = 20):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "frmBusquedaEntesMv:parametroBusqueda_input"))
        )
    except TimeoutException:
        return None

def click_radio_nombre(driver, timeout: int = 10) -> bool:
    """
    Selecciona la opción 'Nombre' (radio). Hay varios envoltorios
    de PrimeFaces; enfocamos el box clickable.
    """
    try:
        box = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='frmBusquedaEntesMv:tipoBusqueda']/tbody/tr/td[2]//div[contains(@class,'ui-radiobutton-box')]"))
        )
        human_click_element(driver, box)
        _sleep(0.2, 0.4)
        return True
    except Exception as e:
        log(f"⚠️ Radio 'Nombre' no clickeable: {e}")
        return False

def press_enter(driver, el) -> None:
    try:
        el.send_keys(Keys.ENTER)
        _sleep(0.3, 0.6)
    except Exception:
        pass

# --------------------
# CAPTCHA
# --------------------
def find_captcha_image(driver, timeout: int = 20):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "frmBusquedaEntesMv:captchaImage"))
        )
    except TimeoutException:
        return None

def find_captcha_input(driver, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "frmBusquedaEntesMv:captcha"))
        )
    except TimeoutException:
        return None

def save_captcha_png(el, path: str) -> str:
    """
    Screenshot SOLO del nodo captcha (más robusto que recortar fullpage).
    """
    el.screenshot(path)
    return path

def find_consultar_button(driver, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "frmBusquedaEntesMv:btnConsultarEnteMv"))
        )
    except TimeoutException:
        return None

# --------------------
# Resultados / Errores
# --------------------
def wait_results_or_error(driver, timeout: int = 35) -> Tuple[str, Optional[str]]:
    """
    Espera a que:
      - Existan resultados (panel con datos) → ('ok', None)
      - Aparezca mensaje de error (p.ej. captcha) → ('captcha_error'|'error', texto)
      - Timeout → ('timeout', None)
    """
    end = time.time() + timeout
    last_err = None

    while time.time() < end:
        try:
            # ¿Mensajes de error?
            errs = driver.find_elements(By.CSS_SELECTOR, ".ui-messages-error, .ui-message-error, .ui-messages-warn")
            if errs:
                txt = " ".join((e.text or "") for e in errs).strip()
                low = txt.lower()
                if any(k in low for k in ["captcha", "imagen", "no coincide", "incorrect"]):
                    return ("captcha_error", txt or None)
                return ("error", txt or None)

            
            # ¿Resultados visibles?
            body_text = (driver.execute_script("return document.body.innerText || ''") or "").lower()
            if ("fideicomiso mercantil inmobiliario" in body_text
            or ("no. inscripción:" in body_text and "fecha inscripción:" in body_text)
            or ("información general" in body_text and "vigente" in body_text)):
                return ("ok", None)

            time.sleep(0.35)
        except Exception as e:
            last_err = str(e)
            time.sleep(0.4)

    return ("timeout", last_err)

# --------------------
# Etapa 1 (preparación + captura captcha)
# --------------------
def stage1_fill_and_capture(driver, query: str, mode: str, captcha_outpath: str) -> bool:
    """
    mode: 'ident' (por defecto) | 'nombre'
    """
    log(f"➡️ Abriendo {MERCADO_VALORES_URL}")
    driver.get(MERCADO_VALORES_URL)
    _sleep(0.7, 1.3)

    if mode == "nombre":
        if not click_radio_nombre(driver):
            log("⚠️ No se pudo seleccionar 'Nombre', se intenta igualmente.")
        _sleep(0.25, 0.5)

    inp = find_main_input(driver, timeout=25)
    if not inp:
        log("❌ No se encontró el input principal.")
        return False

    human_type(inp, query)
    _sleep(0.25, 0.55)
    press_enter(driver, inp)

    # Aparece captcha
    img = find_captcha_image(driver, timeout=25)
    if not img:
        log("❌ No se encontró la imagen del captcha.")
        return False

    save_captcha_png(img, captcha_outpath)
    log(f"📸 MercadoValores: captcha guardado en: {captcha_outpath}")
    return True
