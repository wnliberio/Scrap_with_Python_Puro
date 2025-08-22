#Orquesta el flujo de la página Deudas  Firmes Impugnadas: abrir URL, tipear, provocar validación (TAB), encontrar botón, 
# clic humano, resolver CAPTCHA si aparece, esperar resultados, captura final y salida 
# { "screenshot_path": ... }. Con reintentos y cache como en RUC.

# flows/deudas.py
import time, random
from typing import Optional, Dict

from core.config import SRI_DEUDAS_URL, MAX_RETRIES
from core.browser import create_driver
from core.human import human_type, human_click_element
from core.pages.sri_deudas_page import (
    find_ident_input, find_consultar_button_deudas
)
# Reutilizamos utilidades genéricas del módulo RUC
from core.pages.sri_ruc_page import (
    prepare_for_captcha
)
from core.pages.sri_deudas_page import (
    wait_for_deudas_results
)
from core.captcha.recaptcha import wait_for_recaptcha_solved
from core.utils.log import log
from core.io import cache as cache_io
from core.utils.screenshot import save_fullpage_png

def process_deudas_once(ident: str, headless: bool = False) -> Optional[Dict]:
    """
    ident: cédula (10) o RUC (13)
    """
    driver = create_driver(headless=headless)
    try:
        log(f"➡️ Abriendo {SRI_DEUDAS_URL}")
        driver.get(SRI_DEUDAS_URL)
        time.sleep(random.uniform(0.9, 1.8))

        # 1) Input de identificación
        ident_input = find_ident_input(driver)
        if not ident_input:
            log("⚠️ Deudas: no se encontró el input de cédula/RUC (#busquedaRucId).")
            return None

        human_type(ident_input, ident)
        time.sleep(random.uniform(0.3, 0.7))

        # Forzar blur para que el sitio valide y "aparezca" el botón Consultar
        try:
            ident_input.send_keys(Keys.TAB)
            time.sleep(random.uniform(0.4, 0.8))
        except Exception:
            pass

        # 2) Botón "Consultar"
        btn = find_consultar_button_deudas(driver, timeout=25)
        if not btn:
            log("⚠️ Deudas: no se encontró el botón 'Consultar'.")
            return None

        # 3) Click humano + fallback JS
        try:
            human_click_element(driver, btn)
            time.sleep(random.uniform(0.5, 1.1))
        except Exception as e:
            log(f"⚠️ Deudas: Falló human_click_element: {e}")
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(random.uniform(0.1, 0.3))
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(random.uniform(0.4, 0.9))
                log("✅ Deudas: JS click ejecutado como fallback")
            except Exception as e2:
                log(f"❌ Deudas: Fallback JS click falló: {e2}")
                return None

        # 4) (Posible) reCAPTCHA
        prepare_for_captcha(driver, zoom=1.2)
        if not wait_for_recaptcha_solved(driver):
            log("❌ Deudas: no se pudo resolver el reCAPTCHA")
            return None

        # 5) Esperar resultados visibles
        if not wait_for_deudas_results(driver):
            log("⏳ Deudas: no aparecieron resultados a tiempo.")
            return None

        # 6) ÚNICA captura final
        abs_path = save_fullpage_png(driver, basename=f"sri_deudas_{ident}")
        log(f"📸 Deudas: captura final guardada en: {abs_path}")
        return {"screenshot_path": abs_path}

    finally:
        try:
            driver.quit()
        except Exception:
            pass

def process_deudas(ident: str, headless: bool = False) -> Optional[Dict]:
    """
    Igual patrón de reintentos + cache que en RUC.
    """
    cache = cache_io.load_cache()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- Procesando DEUDAS {ident} (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_deudas_once(ident, headless=headless)
            if data:
                cache[f"deudas:{ident}"] = {
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "data": data
                }
                cache_io.save_cache(cache)
                return data
        except Exception as e:
            log(f"❌ Deudas: Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 3, 20))
    log(f"🛑 Deudas: falló el procesamiento para {ident} tras {MAX_RETRIES} intentos.")
    return None
