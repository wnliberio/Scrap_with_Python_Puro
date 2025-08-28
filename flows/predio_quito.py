# flows/predio_quito.py
import os
import time
import random
from typing import Optional, Dict

from selenium.webdriver.common.by import By

from core.browser import create_driver
from core.human import human_type, human_click_element
from core.utils.screenshot import save_fullpage_png
from core.utils.log import log
from core.io import cache as cache_io
from core.config import MAX_RETRIES

from core.pages.predio_quito_page import (
    PREDIO_QUITO_URL,
    click_tab_apellidos_nombres,
    find_nombres_input,
    find_captcha_image,
    find_captcha_input,
    save_captcha_png,
    find_consultar_button,
    wait_list_or_modal,
    click_first_view_icon,
    wait_detail_state,
    find_historial_button,
)
from core.ocr.azure_ocr import solve_captcha_with_azure

CAPTCHA_DIR = os.path.join("sri_ruc_output", "screenshot_captchas")
os.makedirs(CAPTCHA_DIR, exist_ok=True)

def _safe_name(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (s or ""))[:100]

def _stage1(driver, nombres: str, captcha_out: str) -> bool:
    log(f"➡️ Abriendo {PREDIO_QUITO_URL}")
    driver.get(PREDIO_QUITO_URL)
    time.sleep(random.uniform(0.8, 1.4))

    if not click_tab_apellidos_nombres(driver):
        log("⚠️ No se pudo activar pestaña 'APELLIDOS Y NOMBRES' (seguimos).")

    inp = find_nombres_input(driver, timeout=25)
    if not inp:
        log("❌ Quito: no se encontró el input de Apellidos y Nombres.")
        return False

    # Tipeo humano
    try:
        inp.clear()
    except Exception:
        pass
    human_type(inp, nombres)
    time.sleep(random.uniform(0.25, 0.5))

    # Captcha (nodo)
    img = find_captcha_image(driver, timeout=25)
    if not img:
        log("❌ Quito: no se encontró la imagen del captcha.")
        return False

    save_captcha_png(img, captcha_out)
    log(f"📸 Quito: captcha guardado en: {captcha_out}")
    return True

def process_predio_quito_full(nombres: str, headless: bool = False) -> Optional[Dict]:
    """
    Llenar, resolver captcha, consultar y capturar:
    - Si 'no_records': captura única (estado modal/lista vacía).
    - Si 'list': clic en lupa → detalle:
        - 'pending': screenshot detalle + screenshot historial
        - 'no_pending': screenshot detalle (y si hay botón, historial también)
    """
    driver = create_driver(headless=headless)
    try:
        base = _safe_name(nombres)
        cap_path = os.path.join(CAPTCHA_DIR, f"predio_quito_CAPTCHA_{base}_{time.strftime('%Y%m%d_%H%M%S')}.png")

        if not _stage1(driver, nombres=nombres, captcha_out=cap_path):
            return None

        # OCR – el captcha de Quito es numérico (maxlength=5). Filtramos a dígitos.
        raw = solve_captcha_with_azure(cap_path, attempts=2)
        if not raw:
            log("❌ OCR: Quito no devolvió código.")
            return None
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            log(f"❌ OCR: Quito respondió '{raw}', sin dígitos útiles.")
            return None

        cap_inp = find_captcha_input(driver, timeout=15)
        if not cap_inp:
            log("❌ Quito: no se encontró input del captcha.")
            return None
        try:
            cap_inp.clear()
        except Exception:
            pass
        human_type(cap_inp, digits)
        time.sleep(random.uniform(0.15, 0.35))

        btn = find_consultar_button(driver, timeout=15)
        if not btn:
            log("❌ Quito: no se encontró botón Consultar.")
            return None
        try:
            human_click_element(driver, btn)
        except Exception:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.15)
                driver.execute_script("arguments[0].click();", btn)
            except Exception as e2:
                log(f"❌ Quito: fallback click falló: {e2}")
                return None

        # Esperar listado o modal
        status, _ = wait_list_or_modal(driver, timeout=40)
        if status == "no_records":
            fname = f"predio_quito_no_records_{base}_{time.strftime('%Y%m%d_%H%M%S')}"
            spath = save_fullpage_png(driver, basename=fname)
            log(f"📸 Quito: captura final (sin registros) → {spath}")
            return {"scenario": "no_records", "screenshot_path": spath}

        if status == "list":
            # Abrir la lupa (detalle)
            if not click_first_view_icon(driver, timeout=25):
                # Si no podemos abrir detalle, al menos capturar el listado
                fname = f"predio_quito_listado_{base}_{time.strftime('%Y%m%d_%H%M%S')}"
                spath = save_fullpage_png(driver, basename=fname)
                log(f"📸 Quito: captura listado (no se pudo abrir detalle) → {spath}")
                return {"scenario": "list_only", "screenshot_path": spath}

            # En detalle, clasificar
            dstat, _ = wait_detail_state(driver, timeout=35)

            # Siempre tomar screenshot del detalle
            fname_det = f"predio_quito_detalle_{base}_{time.strftime('%Y%m%d_%H%M%S')}"
            spath_det = save_fullpage_png(driver, basename=fname_det)
            log(f"📸 Quito: captura detalle → {spath_det}")

            # Si hay botón de historial, click y screenshot
            hist_btn = find_historial_button(driver, timeout=8)
            spath_hist = None
            if hist_btn:
                try:
                    human_click_element(driver, hist_btn)
                    time.sleep(random.uniform(1.0, 1.8))  # leve espera a que cargue
                    fname_hist = f"predio_quito_historial_{base}_{time.strftime('%Y%m%d_%H%M%S')}"
                    spath_hist = save_fullpage_png(driver, basename=fname_hist)
                    log(f"📸 Quito: captura historial → {spath_hist}")
                except Exception as e:
                    log(f"⚠️ Quito: no se pudo capturar historial: {e}")

            return {
                "scenario": ("pending" if dstat == "pending" else "no_pending" if dstat == "no_pending" else dstat),
                "screenshot_path": spath_det,
                **({"screenshot_historial_path": spath_hist} if spath_hist else {})
            }

        if status == "timeout":
            log("❌ Quito: timeout esperando listado/modal.")
            return None

        # fallback genérico
        fname = f"predio_quito_unknown_{base}_{time.strftime('%Y%m%d_%H%M%S')}"
        spath = save_fullpage_png(driver, basename=fname)
        log(f"📸 Quito: captura fallback → {spath}")
        return {"scenario": "unknown", "screenshot_path": spath}

    finally:
        try:
            driver.quit()
        except Exception:
            pass

def run_predio_quito(nombres: str, headless: bool = False) -> Optional[Dict]:
    """
    Wrapper con reintentos + cache. Clave: predio_quito:{nombres}
    """
    cache = cache_io.load_cache()
    key = f"predio_quito:{nombres}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- Predio Quito '{nombres}' (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_predio_quito_full(nombres, headless=headless)
            if data:
                cache[key] = {"timestamp": __import__("datetime").datetime.now().isoformat(), "data": data}
                cache_io.save_cache(cache)
                return data
        except Exception as e:
            log(f"❌ Predio Quito: Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 2, 12))
    log(f"🛑 Predio Quito: falló procesamiento para '{nombres}'.")
    return None
