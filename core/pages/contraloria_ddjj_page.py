# core/pages/contraloria_ddjj_page.py
import time
import random
from typing import Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from core.utils.log import log
from core.human import human_type, human_click_element, move_mouse_curve_and_click

CONTRALORIA_DDJJ_URL = "https://www.contraloria.gob.ec/Consultas/DeclaracionesJuradas"


def _sleep(a: float, b: float):
    time.sleep(random.uniform(a, b))

# =========================
# Helpers para coords pantalla
# =========================
def _elem_screen_rect(driver, element):
    """
    Devuelve (left, top, width, height) en coordenadas de pantalla (px) para usar con pyautogui.
    """
    js = """
    const el = arguments[0];
    const r = el.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const sx = (window.screenX || window.screenLeft || 0);
    const sy = (window.screenY || window.screenTop || 0);
    const chromeTop  = (window.outerHeight - window.innerHeight);
    const chromeLeft = (window.outerWidth  - window.innerWidth);
    const left = (sx + r.left + (chromeLeft/2)) * dpr;
    const top  = (sy + r.top  + chromeTop)     * dpr;
    return [left, top, r.width*dpr, r.height*dpr];
    """
    left, top, w, h = driver.execute_script(js, element)
    return float(left), float(top), float(w), float(h)


def _visible(el) -> bool:
    try:
        return el.is_displayed()
    except Exception:
        return False

# -----------------------------
# Banner inicial (cerrar si sale)
# -----------------------------
def dismiss_banner_if_present(driver, timeout: int = 6) -> None:
    """
    Si aparece el overlay #divMensaje, hacemos click **fuera** de la caja blanca usando
    el cursor real (pyautogui via move_mouse_curve_and_click). Nunca clickeamos dentro
    del modal. Fallbacks: click JS en punto seguro, ESC, y ocultar por JS.
    """
    try:
        overlay = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.ID, "divMensaje"))
        )
    except TimeoutException:
        return  # no hay overlay

    # localizar la caja blanca (lo que NO debemos clickear)
    try:
        modal = overlay.find_element(By.CSS_SELECTOR, ".modal-content, .modal-dialog, .modal, .modal-body")
    except Exception:
        modal = None

    # rectángulos en pantalla
    ov_l, ov_t, ov_w, ov_h = _elem_screen_rect(driver, overlay)
    md_rect = None
    if modal:
        md_rect = _elem_screen_rect(driver, modal)

    def outside_modal(px, py) -> bool:
        if not md_rect:
            return True
        ml, mt, mw, mh = md_rect
        return not (ml <= px <= ml + mw and mt <= py <= mt + mh)

    # candidatos "seguros" en el overlay (esquinas)
    margin = 14.0
    candidates = [
        (ov_l + margin,           ov_t + margin),            # top-left
        (ov_l + ov_w - margin,    ov_t + margin),            # top-right
        (ov_l + margin,           ov_t + ov_h - margin),     # bottom-left
        (ov_l + ov_w - margin,    ov_t + ov_h - margin),     # bottom-right
    ]
    safe_points = [(x, y) for (x, y) in candidates if outside_modal(x, y)]
    if not safe_points and md_rect:
        # un punto por encima del modal como emergencia
        ml, mt, mw, mh = md_rect
        safe_points.append((ml + 10, max(ov_t + 8, mt - 12)))

    # 1) Click humano con pyautogui en el primer punto seguro
    for (sx, sy) in safe_points:
        try:
            move_mouse_curve_and_click((sx, sy))
            _sleep(0.18, 0.32)
            if not _visible(overlay):
                return
        except Exception:
            continue

    # 2) Fallback: click por JS en un punto seguro del overlay
    for (sx, sy) in safe_points:
        try:
            driver.execute_script(
                """
                const x = arguments[0], y = arguments[1];
                const el = document.elementFromPoint(x / (window.devicePixelRatio||1),
                                                     y / (window.devicePixelRatio||1));
                if (el) {
                  el.dispatchEvent(new MouseEvent('click', {bubbles:true,cancelable:true,clientX:x,clientY:y}));
                }
                """,
                int(sx), int(sy)
            )
            _sleep(0.15, 0.30)
            if not _visible(overlay):
                return
        except Exception:
            continue

    # 3) Fallback: ESC
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        _sleep(0.15, 0.30)
        if not _visible(overlay):
            return
    except Exception:
        pass

    # 4) Último recurso: ocultar por JS (para no romper el flujo)
    try:
        driver.execute_script("var m=document.getElementById('divMensaje'); if(m){m.style.display='none';}")
        _sleep(0.10, 0.20)
    except Exception:
        pass


# -----------------------------
# Formulario (cédula + captcha)
# -----------------------------
def find_cedula_input(driver, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "txtCedula"))
        )
    except TimeoutException:
        return None


def find_captcha_image(driver, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "captcha"))
        )
    except TimeoutException:
        return None


def find_captcha_input(driver, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "x"))
        )
    except TimeoutException:
        return None


def save_captcha_png(el, path: str) -> str:
    el.screenshot(path)
    return path


def find_buscar_button(driver, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "btnBuscar_in"))
        )
    except TimeoutException:
        return None


def press_enter(el):
    try:
        el.send_keys(Keys.ENTER)
        _sleep(0.2, 0.4)
    except Exception:
        pass


# -----------------------------
# Resultados / errores (post búsqueda)
# -----------------------------
def wait_results_or_error(driver, timeout: int = 40) -> Tuple[str, Optional[str]]:
    """
    ('ok', None)               -> tabla/listado completamente cargado (con indicadores de éxito)
    ('captcha_error', mensaje) -> error de captcha
    ('error', mensaje)         -> otro error visible
    ('timeout', detalle)       -> no concluye a tiempo
    ('retry_needed', None)     -> página no cargó completamente, necesita reintento
    """
    end = time.time() + timeout
    last_err = None

    while time.time() < end:
        try:
            txt = (driver.execute_script("return document.body.innerText || ''") or "").lower()

            # Error de captcha
            if any(k in txt for k in ["captcha", "código de la imagen", "incorrect", "no coincide"]):
                return ("captcha_error", None)

            # Verificar si aún está cargando (evitar screenshot mientras carga)
            if any(k in txt for k in ["cargando", "loading", "procesando", "espere"]):
                log("Detectado estado de carga, esperando...")
                time.sleep(1.0)
                continue

            # INDICADORES DE ÉXITO COMPLETO - página totalmente cargada
            success_indicators = ["sin resultados", "anterior", "siguiente"]
            if any(indicator in txt for indicator in success_indicators):
                log("Página completamente cargada - indicadores de éxito detectados")
                return ("ok", None)

            # Si detectamos contenido de resultados pero sin los indicadores de éxito,
            # esperamos un poco más para que se complete
            if any(k in txt for k in ["apellidos y nombres", "cargo", "entidad", "año"]):
                log("Contenido detectado, esperando indicadores de éxito completo...")
                time.sleep(1.5)
                
                # Verificar nuevamente los indicadores de éxito
                txt_final = (driver.execute_script("return document.body.innerText || ''") or "").lower()
                if any(indicator in txt_final for indicator in success_indicators):
                    log("Indicadores de éxito confirmados después de espera")
                    return ("ok", None)

            time.sleep(0.35)
        except Exception as e:
            last_err = str(e)
            time.sleep(0.4)

    # Si llegamos aquí, timeout sin indicadores de éxito - necesita reintento
    log("Timeout sin indicadores de éxito - requiere reintento de consulta")
    return ("retry_needed", last_err)


# Función adicional para verificar éxito completo
def verify_complete_success(driver) -> bool:
    """
    Verifica que la página muestre los indicadores de carga completa y éxito.
    Retorna True si encuentra 'Sin resultados', 'Anterior', o 'Siguiente'.
    """
    try:
        txt = (driver.execute_script("return document.body.innerText || ''") or "").lower()
        success_indicators = ["sin resultados", "anterior", "siguiente"]
        found = any(indicator in txt for indicator in success_indicators)
        
        if found:
            log("Verificación de éxito: COMPLETADO")
        else:
            log("Verificación de éxito: FALTA - no se encontraron indicadores")
            
        return found
    except Exception as e:
        log(f"Error en verificación de éxito: {e}")
        return False


# -----------------------------
# NUEVA FUNCIÓN: Espera final para screenshot
# -----------------------------
def wait_for_final_screenshot(driver, wait_seconds: float = 3.0) -> None:
    """
    Espera un tiempo antes de tomar el screenshot final para que se carguen bien los resultados.
    Puedes ajustar wait_seconds según necesites (default: 3 segundos).
    """
    log(f"⏳ Esperando {wait_seconds}s para que se carguen completamente los resultados...")
    time.sleep(wait_seconds)
    log("✅ Espera completada, listo para screenshot final")