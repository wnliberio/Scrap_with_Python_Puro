# core/pages/supercias_persona_page.py
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

SUPERCIAS_PERSONA_URL = "https://appscvs1.supercias.gob.ec/consultaPersona/consulta_cia_param.zul"


def _sleep(a: float, b: float):
    time.sleep(random.uniform(a, b))


def _norm(s: str) -> str:
    s = (s or "").strip().upper()
    # normalizar vocales con tilde
    trans = str.maketrans("ÁÉÍÓÚÄËÏÖÜáéíóúäëïöü", "AEIOUAEIOUAEIOUAEIOU")
    return s.translate(trans)


# -----------------------------
# Radios por label (Nombre / Identificación)
# -----------------------------
def _find_radio_input_by_label(driver, label_text: str, timeout: int = 12):
    """
    Busca el <input type="radio"> cuyo label visible coincide con label_text.
    Usa solo el texto del label para tolerar IDs dinámicos.
    """
    wanted = _norm(label_text)
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState==='complete'"))
    except Exception:
        pass

    # Buscar spans .z-radio con label interno
    radios = driver.find_elements(By.CSS_SELECTOR, "span.z-radio")
    for sp in radios:
        try:
            lab = sp.find_element(By.CSS_SELECTOR, "label")
            if _norm(lab.text) == wanted:
                inp = sp.find_element(By.CSS_SELECTOR, "input[type='radio']")
                return inp
        except Exception:
            continue
    return None


def click_radio_nombre(driver, timeout: int = 12) -> bool:
    """
    Hace click humano en el radio 'Nombre' si existe.
    """
    inp = _find_radio_input_by_label(driver, "Nombre", timeout=timeout)
    if not inp:
        log("⚠️ (SuperciasPersona) No se encontró el radio 'Nombre' por label.")
        return False
    try:
        human_click_element(driver, inp)
        _sleep(0.2, 0.4)
        return True
    except Exception as e:
        log(f"⚠️ (SuperciasPersona) Error al clickear radio 'Nombre': {e}")
        try:
            driver.execute_script("arguments[0].click();", inp)
            _sleep(0.15, 0.30)
            return True
        except Exception:
            return False


# -----------------------------
# Inputs por proximidad al radio
# -----------------------------
def _find_input_near_radio_label(driver, label_text: str, timeout: int = 15):
    """
    Encuentra el input 'z-combobox-inp' asociado a la MISMA fila/contenedor
    del radio cuyo label coincide con label_text.
    """
    wanted = _norm(label_text)

    def _candidate():
        radios = driver.find_elements(By.CSS_SELECTOR, "span.z-radio")
        for sp in radios:
            try:
                lab = sp.find_element(By.CSS_SELECTOR, "label")
                if _norm(lab.text) == wanted:
                    # subir al contenedor cercano (fila/row/hbox/div) y buscar input visible
                    anc = sp
                    for _ in range(4):
                        anc = anc.find_element(By.XPATH, "./..")
                        inputs = anc.find_elements(By.CSS_SELECTOR, "input.z-combobox-inp")
                        vis = [i for i in inputs if i.is_displayed() and i.is_enabled()]
                        if vis:
                            return vis[0]
            except Exception:
                continue
        return None

    end = time.time() + timeout
    while time.time() < end:
        el = _candidate()
        if el:
            return el
        time.sleep(0.25)
    return None


def find_ident_input(driver, timeout: int = 15):
    """
    Input de Identificación (Cédula) por cercanía al radio 'Identificación'.
    Si falla, cae a cualquier combobox visible.
    """
    el = _find_input_near_radio_label(driver, "Identificación", timeout=timeout)
    if el:
        return el
    # fallback genérico: primer z-combobox-inp visible
    try:
        cands = driver.find_elements(By.CSS_SELECTOR, "input.z-combobox-inp")
        for i in cands:
            try:
                if i.is_displayed() and i.is_enabled():
                    return i
            except Exception:
                continue
    except Exception:
        pass
    return None


def find_name_input(driver, timeout: int = 15):
    """
    Input para Nombre por cercanía al radio 'Nombre'.
    """
    return _find_input_near_radio_label(driver, "Nombre", timeout=timeout)


def press_enter(el):
    try:
        el.send_keys(Keys.ENTER)
        _sleep(0.3, 0.6)
    except Exception:
        pass


# -----------------------------
# Espera de resultados
# -----------------------------
def wait_results_loaded(driver, timeout: int = 40) -> Tuple[str, str]:
    """
    Devuelve:
      ('ok', '') si se detecta tabla/listado o indicadores de paginación
      ('error', msg) si aparece un mensaje visible de error
      ('timeout', detalle) si no se pudo confirmar
    """
    end = time.time() + timeout
    last_err = ""

    while time.time() < end:
        try:
            # Mensajes de error (container ZK)
            errs = driver.find_elements(By.CSS_SELECTOR, ".z-messagebox, .z-notification, .z-error, .z-errbox")
            if errs:
                txt = " ".join((e.text or "") for e in errs).strip()
                if txt:
                    return ("error", txt)

            # Contenedores de resultados típicos en ZK
            if driver.find_elements(By.CSS_SELECTOR, ".z-listbox, .z-grid, .z-row, .z-listitem"):
                # dar un pequeño settle para completar layout
                _sleep(0.5, 0.9)
                return ("ok", "")

            # Texto en body
            body = (driver.execute_script("return document.body.innerText || ''") or "").lower()
            if any(k in body for k in ["resultados", "lista", "compañía", "cantidad", "razón social", "ruc"]):
                _sleep(0.5, 0.9)
                return ("ok", "")

            time.sleep(0.35)
        except Exception as e:
            last_err = str(e)[:200]
            time.sleep(0.4)

    return ("timeout", last_err or "no se confirmó render de resultados")


# -----------------------------
# Paso de tipeo (ident/nombre)
# -----------------------------
def type_ident(driver, ident: str) -> Optional[object]:
    """
    Tipea cédula en el input de Identificación (no cambia radios).
    """
    el = find_ident_input(driver, timeout=20)
    if not el:
        return None
    human_type(el, ident)
    _sleep(0.25, 0.55)
    return el


def click_nombre_and_type(driver, nombre: str) -> Optional[object]:
    """
    Selecciona el radio 'Nombre' y tipea en el input asociado.
    """
    if not click_radio_nombre(driver, timeout=12):
        log("⚠️ No se pudo seleccionar 'Nombre' (se intentará igual).")
    _sleep(0.2, 0.4)

    el = find_name_input(driver, timeout=20)
    if not el:
        return None
    human_type(el, nombre)
    _sleep(0.25, 0.55)
    return el
