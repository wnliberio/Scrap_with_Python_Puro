# flows/mercado_valores.py
import os
import time
import random
from typing import Optional, Dict

from selenium.webdriver.common.keys import Keys

from core.browser import create_driver
from core.human import human_type, human_click_element
from core.utils.screenshot import save_fullpage_png
from core.utils.log import log
from core.io import cache as cache_io
from core.config import MAX_RETRIES

from core.pages.mercado_valores_page import (
    MERCADO_VALORES_URL,
    stage1_fill_and_capture,
    find_captcha_input,
    find_consultar_button,
    wait_results_or_error,
)
from core.ocr.azure_ocr import solve_captcha_with_azure

CAPTCHA_DIR = os.path.join("sri_ruc_output", "screenshot_captchas")
os.makedirs(CAPTCHA_DIR, exist_ok=True)

def _safe_name(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (s or ""))[:80]

def process_mercado_valores_stage1(query: str, mode: str = "ident", headless: bool = False) -> Optional[Dict]:
    """
    Solo llena, ENTER y captura el captcha (Etapa 1).
    mode: 'ident' | 'nombre'
    """
    driver = create_driver(headless=headless)
    try:
        base = _safe_name(query)
        outpath = os.path.join(CAPTCHA_DIR, f"mercadovalores_CAPTCHA_{base}_{time.strftime('%Y%m%d_%H%M%S')}.png")
        ok = stage1_fill_and_capture(driver, query=query, mode=mode, captcha_outpath=outpath)
        if not ok:
            return None
        return {"captcha_path": os.path.abspath(outpath), "query": query, "mode": mode}
    finally:
        try:
            driver.quit()
        except Exception:
            pass

def process_mercado_valores_full(query: str, mode: str = "ident", headless: bool = False) -> Optional[Dict]:
    """
    Etapa 2:
      - Repite Stage1 (para tener estado fresco) y captura captcha.
      - Lee captcha con Azure OpenAI (alfanumérico / long. variable).
      - Escribe captcha, clic 'Consultar', espera resultados.
      - Captura final única.
      - Un reintento suave si el captcha falla.
    """
    driver = create_driver(headless=headless)
    try:
        # 1) Stage1
        base = _safe_name(query)
        cap_path = os.path.join(CAPTCHA_DIR, f"mercadovalores_CAPTCHA_{base}_{time.strftime('%Y%m%d_%H%M%S')}.png")
        if not stage1_fill_and_capture(driver, query=query, mode=mode, captcha_outpath=cap_path):
            return None

        for attempt in range(1, 3):  # max 2 intentos de captcha
            # 2) OCR
            code = solve_captcha_with_azure(cap_path, attempts=2)
            if not code:
                log("❌ OCR: no se pudo leer el captcha.")
                return None

            # 3) Escribir captcha + Consultar
            cap_inp = find_captcha_input(driver, timeout=15)
            if not cap_inp:
                log("❌ No se encontró el input del captcha.")
                return None

            try:
                cap_inp.clear()
            except Exception:
                pass

            human_type(cap_inp, code)
            time.sleep(random.uniform(0.15, 0.35))

            btn = find_consultar_button(driver, timeout=15)
            if not btn:
                log("❌ No se encontró el botón Consultar.")
                return None

            try:
                human_click_element(driver, btn)
            except Exception:
                # fallback JS
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.15)
                    driver.execute_script("arguments[0].click();", btn)
                except Exception as e2:
                    log(f"❌ Fallback JS click falló: {e2}")
                    return None

            # 4) Esperar resultado o error
            status, msg = wait_results_or_error(driver, timeout=40)
            if status == "ok":
                # 5) Captura final única
                fname = f"mercado_valores_{base}_{time.strftime('%Y%m%d_%H%M%S')}"
                abs_path = save_fullpage_png(driver, basename=fname)
                log(f"📸 MercadoValores: captura final guardada en: {abs_path}")
                return {"screenshot_path": abs_path}

            if status == "captcha_error":
                log(f"⚠️ CAPTCHA incorrecto (intento {attempt}/2): {msg or ''}".strip())
                # El sitio suele refrescar la imagen automáticamente; recapturamos
                new_cap_path = os.path.join(CAPTCHA_DIR, f"mercadovalores_CAPTCHA_{base}_{time.strftime('%Y%m%d_%H%M%S')}.png")
                try:
                    img = driver.find_element(By.ID, "frmBusquedaEntesMv:captchaImage")
                    img.screenshot(new_cap_path)
                    cap_path = new_cap_path
                    log(f"📸 Nuevo captcha guardado en: {new_cap_path}")
                except Exception:
                    log("⚠️ No se pudo recapturar el nuevo captcha; reintentamos con el anterior.")
                continue  # siguiente intento

            if status in ("error", "timeout"):
                log(f"❌ MercadoValores: estado={status} detalle={msg or ''}")
                return None

        log("🛑 MercadoValores: falló por captcha tras 2 intentos.")
        return None

    finally:
        try:
            driver.quit()
        except Exception:
            pass

def run_mercado_valores(query: str, mode: str = "auto", headless: bool = False, solve: bool = False) -> Optional[Dict]:
    """
    Wrapper con reintentos + cache (clave: mercadovalores:{mode}:{query})
    mode: 'auto' | 'ident' | 'nombre'
    """
    mode_final = mode
    if mode == "auto":
        q = (query or "").strip()
        mode_final = "ident" if q.isdigit() else "nombre"

    cache = cache_io.load_cache()
    key = f"mercadovalores:{mode_final}:{query}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- MercadoValores Stage{'2' if solve else '1'} '{query}' (intento {attempt}/{MAX_RETRIES}) ---")
            data = (
                process_mercado_valores_full(query, mode=mode_final, headless=headless)
                if solve else
                process_mercado_valores_stage1(query, mode=mode_final, headless=headless)
            )
            if data:
                cache[key] = {
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "data": data
                }
                cache_io.save_cache(cache)
                return data
        except Exception as e:
            log(f"❌ MercadoValores: Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 2, 14))

    log(f"🛑 MercadoValores: falló el procesamiento para '{query}'.")
    return None
