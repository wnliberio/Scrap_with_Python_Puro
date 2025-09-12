import time, random
from typing import Optional, Dict

from core.config import SRI_URL, MAX_RETRIES
from core.browser import create_driver
from core.human import human_type, human_click_element
from core.pages.sri_ruc_page import (
    find_ruc_input, 
    find_consultar_button, 
    prepare_for_captcha, 
    wait_for_results,
    find_and_click_detail_button,
    detect_ruc_result_state,        # NUEVA
    find_no_results_section         # NUEVA
)
from core.captcha.recaptcha import wait_for_recaptcha_solved
from core.utils.log import log
from core.io import cache as cache_io
from core.utils.screenshot import save_fullpage_png, save_element_screenshot_png

def _ensure_full_content_visible(driver):
    """
    Hace scroll para asegurar que todo el contenido esté visible y no oculto por barras fijas.
    """
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.0)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1.0)
        driver.execute_script("window.scrollBy(0, 100);")
        time.sleep(0.5)
    except Exception as e:
        log(f"⚠️ RUC: Error en scroll preparatorio: {e}")

def process_ruc_once(ruc: str, headless: bool = False) -> Optional[Dict]:
    driver = create_driver(headless=headless)
    try:
        log(f"➡️ Abriendo {SRI_URL}")
        driver.get(SRI_URL)
        time.sleep(random.uniform(0.8, 1.6))

        ruc_input = find_ruc_input(driver)
        if not ruc_input:
            log("⚠️ No se encontró el input de RUC.")
            return None

        human_type(ruc_input, ruc)
        time.sleep(random.uniform(0.3, 0.7))

        # DESPUÉS DE ESCRIBIR EL RUC, DETECTAR QUÉ PASA
        # Esperar un momento para que el sistema responda
        time.sleep(random.uniform(2.0, 3.0))
        
        # NUEVA LÓGICA: Detectar el estado inmediatamente después de escribir el RUC
        search_state = detect_ruc_result_state(driver, timeout=15)
        log(f"🔍 RUC: Estado detectado tras ingresar RUC: {search_state}")

        if search_state == "no_results":
            # ESCENARIO 2: No hay resultados - capturar directamente
            log("📝 RUC: RUC no existe. Tomando captura del mensaje...")
            _ensure_full_content_visible(driver)
            abs_path = save_fullpage_png(driver, f"sri_ruc_no_results_{ruc}")
            log(f"📸 RUC (sin resultados): captura guardada en: {abs_path}")
            return {
                "screenshot_path": abs_path,
                "scenario": "no_results"
            }
        
        # ESCENARIO 1: Hay resultados, buscar botón y continuar flujo normal
        btn = find_consultar_button(driver, timeout=20)
        if not btn:
            log("⚠️ No se encontró el botón 'Consultar'.")
            return None

        try:
            human_click_element(driver, btn)
            time.sleep(random.uniform(0.6, 1.2))
        except Exception as e:
            log(f"⚠️ Falló human_click_element: {e}")
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(random.uniform(0.1, 0.3))
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(random.uniform(0.4, 0.9))
                log("✅ JS click ejecutado como fallback")
            except Exception as e2:
                log(f"❌ Fallback JS click falló: {e2}")
                return None
        
        # reCAPTCHA
        prepare_for_captcha(driver, zoom=1.2)
        if not wait_for_recaptcha_solved(driver):
            log("❌ No se pudo resolver el reCAPTCHA")
            return None
        
        # Esperar resultados completos
        if not wait_for_results(driver):
            log("⏳ No aparecieron resultados a tiempo.")
            return None

        # Hacer clic en botón de detalles adicionales
        detail_clicked = find_and_click_detail_button(driver, timeout=20)
        if detail_clicked:
            log("✅ RUC: Botón de detalles clickeado exitosamente")
            time.sleep(random.uniform(2.0, 3.5))
        else:
            log("⚠️ RUC: No se pudo hacer clic en botón de detalles, continuando...")

        # Capturar página completa con datos
        _ensure_full_content_visible(driver)
        abs_path = save_fullpage_png(driver, f"sri_ruc_{ruc}")
        log(f"📸 RUC (datos completos): captura guardada en: {abs_path}")
        return {
            "screenshot_path": abs_path,
            "scenario": "results_found"
        }

    finally:
        try:
            driver.quit()
        except Exception:
            pass

def process_ruc(ruc: str, headless: bool = False) -> Optional[Dict]:
    cache = cache_io.load_cache()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- Procesando RUC {ruc} (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_ruc_once(ruc, headless=headless)
            if data:
                cache[ruc] = {
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "data": data
                }
                cache_io.save_cache(cache)
                return data
        except Exception as e:
            log(f"❌ Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 3, 20))
    log(f"🛑 Falló el procesamiento para RUC {ruc} tras {MAX_RETRIES} intentos.")
    return None