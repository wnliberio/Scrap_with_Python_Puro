# flows/google_search.py
import time
import random
from typing import Optional, Dict

from selenium.webdriver.common.keys import Keys

from core.browser import create_driver
from core.human import human_type
from core.utils.screenshot import save_fullpage_png
from core.utils.log import log
from core.io import cache as cache_io
from core.config import MAX_RETRIES

from core.pages.google_page import (
    GOOGLE_URL,
    dismiss_consent_if_present,
    find_search_input,
    wait_results_ready,
)


def _final_settle(driver):
    """Breve estabilización antes del screenshot."""
    try:
        # document listo
        for _ in range(5):
            ready = driver.execute_script("return document.readyState==='complete'")
            if ready:
                break
            time.sleep(0.3)
    except Exception:
        pass
    # una pausa humana
    time.sleep(random.uniform(0.6, 1.2))


def process_google_search_once(query: str, headless: bool = False) -> Optional[Dict]:
    driver = create_driver(headless=headless)
    try:
        log(f"➡️ Abriendo {GOOGLE_URL}")
        driver.get(GOOGLE_URL)
        time.sleep(random.uniform(0.7, 1.3))

        # Consentimiento si aparece
        dismiss_consent_if_present(driver)

        # Input
        inp = find_search_input(driver, timeout=20)
        if not inp:
            log("❌ Google: no se encontró el input de búsqueda (#APjFqb/name=q).")
            return None

        # Tipear + ENTER
        human_type(inp, query)
        time.sleep(random.uniform(0.2, 0.45))
        try:
            inp.send_keys(Keys.ENTER)
        except Exception:
            # fallback: botón lupa (si existiera) → enter en body
            try:
                driver.find_element("tag name", "body").send_keys(Keys.ENTER)
            except Exception:
                pass

        # Esperar SERP
        if not wait_results_ready(driver, timeout=30):
            log("⏳ Google: no detectamos resultados a tiempo.")
            return None

        _final_settle(driver)

        # Captura final (única)
        base = "google_" + "_".join(query.strip().split())
        abs_path = save_fullpage_png(driver, basename=base)
        log(f"📸 Google: captura final guardada en: {abs_path}")
        return {"screenshot_path": abs_path}

    finally:
        try:
            driver.quit()
        except Exception:
            pass


def run_google_search(query: str, headless: bool = False) -> Optional[Dict]:
    """
    Reintentos + cache (clave: google:{query})
    """
    cache = cache_io.load_cache()
    key = f"google:{query}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- Google Search '{query}' (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_google_search_once(query, headless=headless)
            if data:
                cache[key] = {
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "data": data
                }
                cache_io.save_cache(cache)
                return data
        except Exception as e:
            log(f"❌ Google: Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 2, 12))

    log(f"🛑 Google: falló el procesamiento para '{query}'.")
    return None
