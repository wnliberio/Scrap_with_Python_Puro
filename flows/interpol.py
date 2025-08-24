# flows/interpol.py
import time, random
from typing import Optional, Dict

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from core.browser import create_driver
from core.human import human_type
from core.utils.log import log
from core.utils.screenshot import save_fullpage_png
from core.io import cache as cache_io
from core.config import MAX_RETRIES

from core.pages.interpol_page import (
    INTERPOL_URL,
    find_surname_input,
    find_forename_input,
    find_submit_button,
    wait_results_list,
    _pick_anchor_index_by_text,
    hover_and_click_name,
    wait_detail_panel,
)

def _final_settle(driver):
    """Pequeña estabilización de render antes de tomar la captura."""
    try:
        WebDriverWait(driver, 5).until(lambda d: d.execute_script("return document.readyState==='complete'"))
    except Exception:
        pass
    # Intentar que todas las imágenes estén completas
    try:
        WebDriverWait(driver, 5).until(
            lambda d: d.execute_script("return (window.__imgs = Array.from(document.images||[])).every(i=>i.complete)")
        )
    except Exception:
        pass
    # Pausa humana corta
    time.sleep(random.uniform(0.8, 1.6))

def process_interpol_once(apellidos_o_full: Optional[str] = "",
                          nombres: Optional[str] = "",
                          headless: bool = False) -> Optional[Dict]:
    """
    Ejecuta 1 vez la búsqueda y retorna {"screenshot_path": "..."}.
    """
    apellidos_o_full = (apellidos_o_full or "").strip()
    nombres = (nombres or "").strip()

    driver = create_driver(headless=headless)
    try:
        log(f"➡️ Abriendo {INTERPOL_URL}")
        driver.get(INTERPOL_URL)
        time.sleep(random.uniform(0.7, 1.4))

        # Inputs
        inp_last = find_surname_input(driver)
        if not inp_last:
            log("⚠️ INTERPOL: no se encontró el input de Apellidos (#name).")
            return None

        human_type(inp_last, apellidos_o_full)
        time.sleep(random.uniform(0.2, 0.45))

        if nombres:
            inp_name = find_forename_input(driver)
            if inp_name:
                human_type(inp_name, nombres)
                time.sleep(random.uniform(0.2, 0.45))

        # Buscar
        btn = find_submit_button(driver)
        if not btn:
            log("⚠️ INTERPOL: no se encontró el botón Buscar (#submit).")
            return None
        btn.send_keys(Keys.ENTER)
        time.sleep(random.uniform(0.4, 0.8))

        # Esperar lista
        if not wait_results_list(driver, timeout=40):
            log("⏳ INTERPOL: no aparecieron resultados.")
            return None

        # Elegir mejor match por texto y hacer hover/click
        wanted_text = f"{apellidos_o_full} {nombres}".strip()
        idx = _pick_anchor_index_by_text(driver, wanted_text) or 1

        if not hover_and_click_name(driver, idx):
            log("⏳ INTERPOL: no se pudo hacer clic sobre el nombre; capturamos la lista.")
            abs_path = save_fullpage_png(driver, basename="interpol_lista")
            log(f"📸 INTERPOL (lista): captura guardada en: {abs_path}")
            return {"screenshot_path": abs_path}

        # Esperar panel detalle (con .wantedsingle__colright)
        if not wait_detail_panel(driver, timeout=45):
            log("⏳ INTERPOL: no cargó el panel de detalle; capturamos la lista como fallback.")
            abs_path = save_fullpage_png(driver, basename="interpol_lista")
            log(f"📸 INTERPOL (lista): captura guardada en: {abs_path}")
            return {"screenshot_path": abs_path}

        # Settle final para que carguen textos/imagenes/estilos
        _final_settle(driver)

        # Captura final (única)
        base = "interpol_" + "_".join([s.replace(" ", "_") for s in [apellidos_o_full, nombres] if s]) or "interpol_detalle"
        abs_path = save_fullpage_png(driver, basename=base)
        log(f"📸 INTERPOL: captura final guardada en: {abs_path}")
        return {"screenshot_path": abs_path}

    finally:
        try:
            driver.quit()
        except Exception:
            pass

def run_interpol_search(apellidos_o_full: Optional[str] = "",
                        nombres: Optional[str] = "",
                        headless: bool = False) -> Optional[Dict]:
    """
    Wrapper con reintentos + cache, mismo patrón que los otros flows.
    """
    apellidos_o_full = (apellidos_o_full or "").strip()
    nombres = (nombres or "").strip()

    cache = cache_io.load_cache()
    key = f"interpol:{apellidos_o_full}|{nombres}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- Procesando INTERPOL {key} (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_interpol_once(apellidos_o_full, nombres, headless=headless)
            if data:
                cache[key] = {
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "data": data
                }
                cache_io.save_cache(cache)
                return data
        except Exception as e:
            log(f"❌ INTERPOL: Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 3, 18))

    log(f"🛑 INTERPOL: falló el procesamiento para {key}.")
    return None

# Retro-compatibilidad
def process_interpol(apellidos: Optional[str] = "", nombres: Optional[str] = "", headless: bool = False):
    return run_interpol_search(apellidos_o_full=apellidos, nombres=nombres, headless=headless)

__all__ = ["process_interpol_once", "run_interpol_search", "process_interpol"]
