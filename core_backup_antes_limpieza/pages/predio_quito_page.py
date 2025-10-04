# core/pages/predio_quito_page.py
import time
import random
from typing import Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from core.utils.log import log
from core.human import human_type, human_click_element

PREDIO_QUITO_URL = "https://pam.quito.gob.ec/Consultaobligaciones/"

def _sleep(a: float, b: float):
    time.sleep(random.uniform(a, b))

# -----------------------------
# Finders / actions (form)
# -----------------------------
def click_tab_apellidos_nombres(driver, timeout: int = 15) -> bool:
    """
    Selecciona la pestaña 'APELLIDOS Y NOMBRES'.
    Preferimos ID directo; si falla, buscamos por texto.
    """
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "__tab_TcOpciones_TbpApellidosNombres"))
        )
        human_click_element(driver, el)
        _sleep(0.25, 0.5)
        return True
    except Exception:
        # fallback por texto visible
        try:
            el = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='APELLIDOS Y NOMBRES']"))
            )
            human_click_element(driver, el)
            _sleep(0.25, 0.5)
            return True
        except Exception as e2:
            log(f"⚠️ No se pudo seleccionar pestaña 'APELLIDOS Y NOMBRES': {e2}")
            return False

def find_nombres_input(driver, timeout: int = 20):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "TcOpciones_TbpApellidosNombres_TxtApellidosNombres"))
        )
    except TimeoutException:
        return None

def find_captcha_image(driver, timeout: int = 20):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "TcOpciones_TbpApellidosNombres_RcApellidosNombres_CaptchaImage"))
        )
    except TimeoutException:
        return None

def find_captcha_input(driver, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "TcOpciones_TbpApellidosNombres_TxtCaptchaApellidosNombres"))
        )
    except TimeoutException:
        return None

def save_captcha_png(el, outpath: str) -> str:
    el.screenshot(outpath)
    return outpath

def find_consultar_button(driver, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "TcOpciones_TbpApellidosNombres_LkbConsultarApellidosNombres"))
        )
    except TimeoutException:
        return None

# -----------------------------
# Resultados / navegación
# -----------------------------
def wait_list_or_modal(driver, timeout: int = 30) -> Tuple[str, Optional[str]]:
    """
    Espera listado o modal de 'No existen registros'
    Retorna:
      ('no_records', msg)  si aparece modal/mensaje
      ('list', None)       si aparece la tabla de resultados
      ('timeout', detalle) si no hay nada
    """
    end = time.time() + timeout
    last_err = None
    while time.time() < end:
        try:
            body = (driver.execute_script("return document.body.innerText || ''") or "").lower()
            # Modal / aviso sin registros
            if "no existen registros" in body and "apellidos y nombres" in body:
                return ("no_records", None)

            # Tabla de resultados (hay un <table> con columna 'VER')
            tables = driver.find_elements(By.CSS_SELECTOR, "main table.table, main table")
            if tables:
                # asegurarnos que tenga filas
                for t in tables:
                    try:
                        if t.find_elements(By.CSS_SELECTOR, "tbody tr"):
                            return ("list", None)
                    except StaleElementReferenceException:
                        continue

            time.sleep(0.35)
        except Exception as e:
            last_err = str(e)
            time.sleep(0.4)

    return ("timeout", last_err)

def click_first_view_icon(driver, timeout: int = 20) -> bool:
    """
    En el listado, clic a la primera lupa (columna VER).
    """
    try:
        # Variante robusta: primer <a> en última columna de la primera fila
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, "(//main//table//tbody/tr[1]//td[last()]//a)[1]")
            )
        )
        human_click_element(driver, el)
        _sleep(0.4, 0.7)
        return True
    except Exception as e:
        log(f"⚠️ No se pudo hacer clic en la lupa de 'VER': {e}")
        return False

def wait_detail_state(driver, timeout: int = 35) -> Tuple[str, Optional[str]]:
    """
    En la vista de detalle:
      ('pending', None)       si hay 'Pendiente' o 'Total adeudado'
      ('no_pending', None)    si hay 'No existen valores pendientes'
      ('unknown', txt)        si no podemos clasificar
      ('timeout', err)        si expira
    """
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            txt = (driver.execute_script("return document.body.innerText || ''") or "").lower()

            if "no existen valores pendientes de pago" in txt:
                return ("no_pending", None)
            if ("pendiente" in txt) or ("total adeudado" in txt):
                return ("pending", None)

            last = txt[:180]
            time.sleep(0.4)
        except Exception as e:
            last = str(e)
            time.sleep(0.4)
    return ("timeout", last)

def find_historial_button(driver, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "btnHistorialPagos"))
        )
    except TimeoutException:
        return None
