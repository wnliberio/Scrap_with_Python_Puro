# flows/mercado_valores.py
import os
import re
import time
import random
from typing import Optional, Dict

from selenium.webdriver.common.keys import Keys

from core.browser import create_driver
from core.human import human_type
from core.utils.log import log
from core.config import MAX_RETRIES
from core.utils.screenshot import save_fullpage_png  # (no lo usamos aún, pero queda listo)

from core.pages.mercado_valores_page import (
    MERCADO_VALORES_URL,
    find_param_input,
    select_mode_nombre,
    wait_after_enter,
    click_first_autocomplete_if_any,
    wait_captcha_ready,
)


def _ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^\w\-\.]+", "_", s)
    return s[:80] or "valor"


def process_mercado_valores_once(
    valor: str,
    modo: Optional[str] = None,  # "ident" | "nombre" | None (autodetect)
    headless: bool = False,
) -> Optional[Dict]:
    """
    Etapa 1:
      - Abrir URL
      - Seleccionar modo (si corresponde)
      - Tipear valor y presionar ENTER
      - Esperar que aparezca el captcha
      - Hacer node-screenshot del captcha y guardarlo en sri_ruc_output/screenshot_captchas/
      - Devolver { captcha_path, query, mode }
    """
    valor = (valor or "").strip()
    if not valor:
        log("⚠️ MercadoValores: valor vacío.")
        return None

    # Autodetección simple: solo dígitos 10-13 = identificación
    if modo not in ("ident", "nombre"):
        modo = "ident" if re.fullmatch(r"\d{10,13}", valor) else "nombre"

    driver = create_driver(headless=headless)
    try:
        log(f"➡️ Abriendo {MERCADO_VALORES_URL}")
        driver.get(MERCADO_VALORES_URL)
        time.sleep(random.uniform(0.7, 1.4))

        # Modo nombre: cambiar el radio
        if modo == "nombre":
            if not select_mode_nombre(driver):
                log("⚠️ No se pudo cambiar a modo 'Nombre'. Continuo igualmente…")
            time.sleep(random.uniform(0.25, 0.45))

        # Input
        inp = find_param_input(driver)
        if not inp:
            log("⚠️ MercadoValores: no se encontró el input de búsqueda.")
            return None

        # Tipeo humano y ENTER
        inp.clear()
        human_type(inp, valor)
        time.sleep(random.uniform(0.25, 0.45))
        inp.send_keys(Keys.ENTER)
        time.sleep(random.uniform(0.35, 0.65))

        # Esperar post-ENTER
        if not wait_after_enter(driver, timeout=16):
            # Fallback: aceptar primer autocomplete y volver a esperar
            if click_first_autocomplete_if_any(driver):
                if not wait_after_enter(driver, timeout=12):
                    log("⏳ MercadoValores: no aparecieron datos/captcha tras seleccionar autocomplete.")
                    return None
            else:
                log("⏳ MercadoValores: no aparecieron datos/captcha tras ENTER.")
                return None

        # Captcha listo
        captcha_el = wait_captcha_ready(driver, timeout=14)
        if not captcha_el:
            log("⏳ MercadoValores: no apareció el captcha.")
            return None

        # Guardar node-screenshot
        base_dir = os.path.join("sri_ruc_output", "screenshot_captchas")
        _ensure_dir(base_dir)
        fname = f"mercadovalores_CAPTCHA_{_norm(valor)}_{time.strftime('%Y%m%d_%H%M%S')}.png"
        fpath = os.path.abspath(os.path.join(base_dir, fname))
        captcha_el.screenshot(fpath)
        log(f"📸 MercadoValores: captcha guardado en: {fpath}")

        return {"captcha_path": fpath, "query": valor, "mode": modo}

    finally:
        try:
            driver.quit()
        except Exception:
            pass


def run_mercado_valores_stage1(
    valor: str, modo: Optional[str] = None, headless: bool = False
) -> Optional[Dict]:
    """
    Wrapper con reintentos (no cacheamos porque el captcha cambia).
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- MercadoValores Stage1 '{valor}' (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_mercado_valores_once(valor, modo=modo, headless=headless)
            if data:
                return data
        except Exception as e:
            log(f"❌ MercadoValores: Error en intento {attempt}: {e}")
            time.sleep(min(2 + attempt * 3, 18))
    log(f"🛑 MercadoValores: falló la obtención del captcha para '{valor}'.")
    return None
