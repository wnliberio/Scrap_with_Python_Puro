# flows/denuncias.py
#  Flujo completo: abrir, tipear, clic, (si hubiera) CAPTCHA, esperar resultados y una captura final.
import time, random
from typing import Optional, Dict
from selenium.webdriver.common.keys import Keys

from core.config import FISCALIAS_DENUNCIAS_URL, MAX_RETRIES
from core.browser import create_driver
from core.human import human_type, human_click_element
from core.pages.denuncias_page import (
    find_name_input, find_search_button, wait_for_denuncias_results
)
from core.pages.sri_ruc_page import prepare_for_captcha  # genérico
from core.captcha.recaptcha import wait_for_recaptcha_solved
from core.utils.log import log
from core.io import cache as cache_io
from core.utils.screenshot import save_fullpage_png
from selenium.webdriver.common.by import By

def _maybe_solve_recaptcha(driver) -> bool:
    """
    Verifica si hay reCAPTCHA visible y, si lo hay, intenta resolverlo.
    Si no hay, devuelve True (no bloquea).
    """
    try:
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
        if not any(f.is_displayed() for f in iframes):
            log("[CAPTCHA] 👍 No hay reCAPTCHA presente (Denuncias)")
            return True

        # Si aparece, usa el mismo pipeline que en SRI
        log("[CAPTCHA] 🔍 reCAPTCHA detectado (Denuncias). Intentando resolver…")
        prepare_for_captcha(driver, zoom=1.2)
        return wait_for_recaptcha_solved(driver)
    except Exception as e:
        log(f"[CAPTCHA] ⚠️ Detección CAPTCHA (Denuncias) falló: {e}")
        return True  # no bloquea si falla la detección

def process_denuncias_once(nombre_completo: str, headless: bool = False) -> Optional[Dict]:
    driver = create_driver(headless=headless)
    try:
        log(f"➡️ Abriendo {FISCALIAS_DENUNCIAS_URL}")
        driver.get(FISCALIAS_DENUNCIAS_URL)
        time.sleep(random.uniform(0.8, 1.6))

        # 1) Input nombres completos
        name_input = find_name_input(driver)
        if not name_input:
            log("⚠️ Denuncias: no se encontró el input #pwd.")
            return None

        human_type(name_input, nombre_completo)
        time.sleep(random.uniform(0.25, 0.6))
        try:
            name_input.send_keys(Keys.TAB)  # dispara validaciones oninput si las hay
            time.sleep(random.uniform(0.3, 0.6))
        except Exception:
            pass

        # 2) Botón Buscar
        btn = find_search_button(driver, timeout=15)
        if not btn:
            log("⚠️ Denuncias: no se encontró el botón 'Buscar Denuncia'.")
            return None

        try:
            human_click_element(driver, btn)
            time.sleep(random.uniform(0.6, 1.2))
        except Exception as e:
            log(f"⚠️ Denuncias: Falló human_click_element: {e}")
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(random.uniform(0.1, 0.3))
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(random.uniform(0.4, 0.9))
                log("✅ Denuncias: JS click ejecutado como fallback")
            except Exception as e2:
                log(f"❌ Denuncias: Fallback JS click falló: {e2}")
                return None

        # 3) (Posible) reCAPTCHA
        if not _maybe_solve_recaptcha(driver):
            log("❌ Denuncias: no se pudo resolver el reCAPTCHA")
            return None

        # 4) Esperar resultados
        if not wait_for_denuncias_results(driver):
            log("⏳ Denuncias: no se detectó contenedor de resultados; tomando captura de todos modos…")
            time.sleep(2.5)

        # 5) ÚNICA captura final
        abs_path = save_fullpage_png(driver, basename=f"fiscalias_denuncias_{_slug(nombre_completo)}")
        log(f"📸 Denuncias: captura final guardada en: {abs_path}")
        return {"screenshot_path": abs_path}

    finally:
        try:
            driver.quit()
        except Exception:
            pass

def process_denuncias(nombre_completo: str, headless: bool = False) -> Optional[Dict]:
    cache = cache_io.load_cache()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- Procesando DENUNCIAS '{nombre_completo}' (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_denuncias_once(nombre_completo, headless=headless)
            if data:
                cache_key = f"denuncias:{nombre_completo}"
                cache[cache_key] = {
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "data": data
                }
                cache_io.save_cache(cache)
                return data
        except Exception as e:
            log(f"❌ Denuncias: Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 2, 12))
    log(f"🛑 Denuncias: falló el procesamiento para '{nombre_completo}' tras {MAX_RETRIES} intentos.")
    return None

def _slug(text: str) -> str:
    import re
    t = re.sub(r"\s+", "_", text.strip())
    t = re.sub(r"[^\w\-]+", "", t)
    return t[:40] or "consulta"
