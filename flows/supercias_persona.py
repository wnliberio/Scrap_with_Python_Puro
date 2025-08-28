# flows/supercias_persona.py
import time
import random
from typing import Optional, Dict

from core.browser import create_driver
from core.utils.screenshot import save_fullpage_png
from core.utils.log import log
from core.io import cache as cache_io
from core.config import MAX_RETRIES

from core.pages.supercias_persona_page import (
    SUPERCIAS_PERSONA_URL,
    type_ident,
    click_nombre_and_type,
    press_enter,
    wait_results_loaded,
)


def _safe_name(s: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in (s or ""))[:80]


def _detect_mode(query: str) -> str:
    q = (query or "").strip()
    return "ident" if q.isdigit() and len(q) == 10 else "nombre"


def process_supercias_persona_once(query: str, mode: str = "auto", headless: bool = False) -> Optional[Dict]:
    """
    Abre la página, decide modo (ident/nombre), tipea, ENTER, espera resultados y captura única.
    """
    mode_final = _detect_mode(query) if mode == "auto" else mode
    base = _safe_name(query)

    driver = create_driver(headless=headless)
    try:
        log(f"➡️ Abriendo {SUPERCIAS_PERSONA_URL}")
        driver.get(SUPERCIAS_PERSONA_URL)
        time.sleep(random.uniform(0.7, 1.3))

        # Tipeo según modo
        if mode_final == "ident":
            field = type_ident(driver, query)
        else:
            field = click_nombre_and_type(driver, query)

        if not field:
            log("❌ SuperciasPersona: no se encontró el input para tipear.")
            return None

        # ENTER para disparar búsqueda
        press_enter(field)

        # Esperar resultados
        status, msg = wait_results_loaded(driver, timeout=45)
        if status != "ok":
            log(f"❌ SuperciasPersona: estado={status} detalle={msg or ''}")
            return None

        # Captura final única
        fname = f"supercias_persona_{mode_final}_{base}_{time.strftime('%Y%m%d_%H%M%S')}"
        abs_path = save_fullpage_png(driver, basename=fname)
        log(f"📸 SuperciasPersona: captura final guardada en: {abs_path}")
        return {"screenshot_path": abs_path}

    finally:
        try:
            driver.quit()
        except Exception:
            pass


def run_supercias_persona(query: str, mode: str = "auto", headless: bool = False) -> Optional[Dict]:
    """
    Wrapper con reintentos + cache.
    Clave: supercias_persona:{mode_final}:{query}
    """
    mode_final = _detect_mode(query) if mode == "auto" else mode
    cache = cache_io.load_cache()
    key = f"supercias_persona:{mode_final}:{query}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- SuperciasPersona '{query}' modo={mode_final} (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_supercias_persona_once(query, mode=mode_final, headless=headless)
            if data:
                cache[key] = {
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "data": data
                }
                cache_io.save_cache(cache)
                return data
        except Exception as e:
            log(f"❌ SuperciasPersona: Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 2, 14))

    log(f"🛑 SuperciasPersona: falló el procesamiento para '{query}'.")
    return None
