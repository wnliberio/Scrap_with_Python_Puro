# flows/contraloria_ddjj.py
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

from core.pages.contraloria_ddjj_page import (
    CONTRALORIA_DDJJ_URL,
    dismiss_banner_if_present,
    find_cedula_input,
    find_captcha_image,
    find_captcha_input,
    save_captcha_png,
    find_buscar_button,
    wait_results_or_error,
)

from core.ocr.azure_ocr import solve_captcha_with_azure

CAPTCHA_DIR = os.path.join("sri_ruc_output", "screenshot_captchas")
os.makedirs(CAPTCHA_DIR, exist_ok=True)


def _safe_name(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (s or ""))[:80]


def _stage1_fill_and_capture(driver, cedula: str, captcha_outpath: str) -> bool:
    log(f"➡️ Abriendo {CONTRALORIA_DDJJ_URL}")
    driver.get(CONTRALORIA_DDJJ_URL)
    time.sleep(random.uniform(0.7, 1.3))

    # Cerrar banner si aparece
    dismiss_banner_if_present(driver)

    # Cédula (10 dígitos)
    inp = find_cedula_input(driver, timeout=20)
    if not inp:
        log("❌ Contraloría: no se encontró el input de cédula (#txtCedula).")
        return False

    human_type(inp, cedula)
    time.sleep(random.uniform(0.25, 0.55))

    # Captcha (nodo puntual)
    img = find_captcha_image(driver, timeout=20)
    if not img:
        log("❌ Contraloría: no se encontró la imagen del captcha (#captcha).")
        return False

    save_captcha_png(img, captcha_outpath)
    log(f"📸 Contraloría: captcha guardado en: {captcha_outpath}")
    return True


def process_contraloria_stage1(cedula: str, headless: bool = False) -> Optional[Dict]:
    """
    Etapa 1: solo llega hasta capturar la imagen del captcha.
    """
    driver = create_driver(headless=headless)
    try:
        base = _safe_name(cedula)
        cap_path = os.path.join(CAPTCHA_DIR, f"contraloria_CAPTCHA_{base}_{time.strftime('%Y%m%d_%H%M%S')}.png")
        ok = _stage1_fill_and_capture(driver, cedula=cedula, captcha_outpath=cap_path)
        if not ok:
            return None
        return {"captcha_path": os.path.abspath(cap_path), "cedula": cedula}
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def process_contraloria_full(cedula: str, headless: bool = False) -> Optional[Dict]:
    """
    Etapa 2 completa:
      - Repite Stage1 (estado fresco) y captura captcha.
      - Invoca Azure OCR.
      - Tipea código, clic en Buscar.
      - Espera resultados.
      - Captura final única.
      - Reintenta una vez si el captcha fue rechazado.
    """
    driver = create_driver(headless=headless)
    try:
        base = _safe_name(cedula)
        cap_path = os.path.join(CAPTCHA_DIR, f"contraloria_CAPTCHA_{base}_{time.strftime('%Y%m%d_%H%M%S')}.png")
        if not _stage1_fill_and_capture(driver, cedula=cedula, captcha_outpath=cap_path):
            return None

        for attempt in range(1, 3):  # hasta 2 intentos de captcha
            # OCR
            code = solve_captcha_with_azure(cap_path, attempts=2)
            if not code:
                log("❌ OCR: no se pudo leer el captcha.")
                return None

            # Escribir captcha
            cap_inp = find_captcha_input(driver, timeout=15)
            if not cap_inp:
                log("❌ Contraloría: no se encontró el input del captcha (#x).")
                return None

            try:
                cap_inp.clear()
            except Exception:
                pass
            human_type(cap_inp, code)
            time.sleep(random.uniform(0.15, 0.35))

            # Click Buscar
            btn = find_buscar_button(driver, timeout=15)
            if not btn:
                log("❌ Contraloría: no se encontró el botón Buscar (#btnBuscar_in).")
                return None

            try:
                human_click_element(driver, btn)
            except Exception:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.15)
                    driver.execute_script("arguments[0].click();", btn)
                except Exception as e2:
                    log(f"❌ Contraloría: Fallback JS click falló: {e2}")
                    return None

            # Esperar respuesta
            status, msg = wait_results_or_error(driver, timeout=45)
            if status == "ok":
                fname = f"contraloria_ddjj_{base}_{time.strftime('%Y%m%d_%H%M%S')}"
                abs_path = save_fullpage_png(driver, basename=fname)
                log(f"📸 Contraloría: captura final guardada en: {abs_path}")
                return {"screenshot_path": abs_path}

            if status == "captcha_error":
                log(f"⚠️ Captcha incorrecto (intento {attempt}/2). Recapturando…")
                # recapturar imagen (suele cambiar sola; si no, re-usa la misma)
                try:
                    img = find_captcha_image(driver, timeout=10)
                    if img:
                        cap_path = os.path.join(CAPTCHA_DIR, f"contraloria_CAPTCHA_{base}_{time.strftime('%Y%m%d_%H%M%S')}.png")
                        img.screenshot(cap_path)
                        log(f"📸 Nuevo captcha guardado en: {cap_path}")
                except Exception:
                    pass
                continue

            if status in ("error", "timeout"):
                log(f"❌ Contraloría: estado={status} detalle={msg or ''}")
                return None

        log("🛑 Contraloría: falló por captcha tras 2 intentos.")
        return None

    finally:
        try:
            driver.quit()
        except Exception:
            pass


def run_contraloria_ddjj(cedula: str, solve: bool = True, headless: bool = False) -> Optional[Dict]:
    """
    Wrapper con reintentos + cache. Clave: contraloria:{cedula}:{stage}
    """
    cache = cache_io.load_cache()
    key = f"contraloria:{cedula}:{'stage2' if solve else 'stage1'}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- Contraloría DDJJ {'Stage2' if solve else 'Stage1'} {cedula} (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_contraloria_full(cedula, headless=headless) if solve else process_contraloria_stage1(cedula, headless=headless)
            if data:
                cache[key] = {
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "data": data
                }
                cache_io.save_cache(cache)
                return data
        except Exception as e:
            log(f"❌ Contraloría: Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 2, 14))

    log(f"🛑 Contraloría: falló el procesamiento para {cedula}.")
    return None
