import time
import random
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from core.utils.log import log
from core.human import human_type, human_click_element, move_mouse_curve_and_click

PREDIO_MANTA_URL = "https://portalciudadano.manta.gob.ec/consulta"

def _sleep(a: float, b: float):
    time.sleep(random.uniform(a, b))

# --------------------
# Helpers pantalla (para intentar cerrar la burbuja de geolocalización)
# --------------------
def _viewport_top_right_screen_xy(driver, offset_x=50, offset_y=80):
    js = """
    const dpr = window.devicePixelRatio || 1;
    const sx = (window.screenX || window.screenLeft || 0);
    const sy = (window.screenY || window.screenTop || 0);
    const chromeTop  = (window.outerHeight - window.innerHeight);
    const chromeLeft = (window.outerWidth  - window.innerWidth);
    const x = sx + window.innerWidth - (chromeLeft/2) - arguments[0];
    const y = sy + (chromeTop) + arguments[1];
    return [x*dpr, y*dpr, dpr];
    """
    x, y, _ = driver.execute_script(js, int(offset_x), int(offset_y))
    return (float(x), float(y))

def try_close_geo_prompt(driver) -> None:
    """
    Intenta cerrar el popup de geolocalización. Primero buscamos un posible botón 'X'
    dentro del DOM (si fuese un modal propio del sitio). Si no, hacemos un click humano
    hacia la esquina superior-derecha del viewport (suele estar el 'X' del prompt del navegador).
    Esto es 'best-effort'; si no existe, seguimos.
    """
    # 1) Intento DOM
    candidates = [
        (By.CSS_SELECTOR, "button.swal2-close"),
        (By.CSS_SELECTOR, ".modal .close"),
        (By.CSS_SELECTOR, "button[aria-label='Close']"),
        (By.XPATH, "//button[contains(., '×') or contains(., 'Cerrar') or contains(., 'close')]"),
    ]
    for how, sel in candidates:
        try:
            el = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((how, sel)))
            human_click_element(driver, el)
            _sleep(0.2, 0.4)
            return
        except TimeoutException:
            pass
        except Exception:
            pass

    # 2) Intento de click “a ciegas” en la esquina superior derecha
    try:
        x, y = _viewport_top_right_screen_xy(driver, offset_x=46, offset_y=70)
        move_mouse_curve_and_click((x, y))
        _sleep(0.15, 0.30)
    except Exception:
        pass

# --------------------
# Selectores básicos
# --------------------
def wait_ready(driver, timeout: int = 20) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "tipo_documento"))
        )
        return True
    except TimeoutException:
        return False

def open_tipo_dropdown(driver, timeout: int = 10):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "tipo_documento"))
        )
        human_click_element(driver, el)
        _sleep(0.15, 0.35)
        return el
    except TimeoutException:
        return None

def choose_tipo(driver, visible_text: str, timeout: int = 10) -> bool:
    """
    visible_text: "Cédula / RUC / Pasaporte"  |  "Apellidos / Nombres"
    """
    try:
        sel_el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "tipo_documento"))
        )
        Select(sel_el).select_by_visible_text(visible_text)
        _sleep(0.15, 0.30)
        return True
    except Exception:
        # fallback por click directo
        try:
            opt = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, f"//select[@id='tipo_documento']/option[normalize-space()='{visible_text}']"))
            )
            human_click_element(driver, opt)
            _sleep(0.15, 0.30)
            return True
        except Exception:
            return False

def find_txtclave(driver, timeout: int = 10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "txtclave"))
        )
    except TimeoutException:
        return None

def find_btn_buscar(driver, timeout: int = 10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "btnbuscar_2"))
        )
    except TimeoutException:
        return None

def wait_results(driver, timeout: int = 25) -> None:
    """
    Espera pasiva a que la página muestre resultados (no hay selector único).
    Usamos un pequeño loop para dar tiempo a que dibuje y luego capturamos.
    """
    end = time.time() + timeout
    last_len = 0
    while time.time() < end:
        try:
            txt = (driver.execute_script("return document.body.innerText||''") or "")
            if len(txt) != last_len:
                last_len = len(txt)
                _sleep(0.4, 0.8)
            else:
                break
        except Exception:
            _sleep(0.5, 0.9)
