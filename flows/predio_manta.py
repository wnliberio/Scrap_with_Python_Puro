import os
import time
import random
from typing import Optional, Dict
import re

from core.browser import create_driver
from core.human import human_type, human_click_element
from core.utils.screenshot import save_fullpage_png
from core.utils.log import log

from core.pages.predio_manta_page import (
    PREDIO_MANTA_URL,
    try_close_geo_prompt,
    wait_ready,
    open_tipo_dropdown,
    choose_tipo,
    find_txtclave,
    find_btn_buscar,
    wait_results,
)

def _safe_name(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (s or ""))[:100]

def _classify_value(v: str) -> str:
    """
    Retorna:
      - 'doc' -> Cédula (10), RUC (13) o Pasaporte (3 letras + 6 dígitos)
      - 'nombre' -> caso contrario
    """
    vv = (v or "").strip()
    if vv.isdigit() and len(vv) in (10, 13):
        return "doc"
    if re.fullmatch(r"[A-Za-z]{3}\d{6}", vv):
        return "doc"
    return "nombre"

def run_predio_manta(valor: str, headless: bool = False) -> Optional[Dict]:
    """
    Abre Manta, cierra prompt de geolocalización (si aparece), selecciona tipo,
    escribe el valor, busca y captura una screenshot final.
    """
    driver = create_driver(headless=headless)
    try:
        log(f"➡️ Abriendo {PREDIO_MANTA_URL}")
        driver.get(PREDIO_MANTA_URL)
        time.sleep(random.uniform(0.8, 1.4))

        # cerrar “Conocer tu ubicación” si aparece
        try_close_geo_prompt(driver)

        if not wait_ready(driver, timeout=20):
            log("❌ Manta: no cargó el selector #tipo_documento.")
            return None

        # Seleccionar tipo según valor
        tipo = _classify_value(valor)
        open_tipo_dropdown(driver)
        if tipo == "doc":
            ok = choose_tipo(driver, "Cédula / RUC / Pasaporte", timeout=10)
        else:
            ok = choose_tipo(driver, "Apellidos / Nombres", timeout=10)
        if not ok:
            log("⚠️ Manta: no se pudo seleccionar la opción del tipo. Continuo igualmente…")

        # Escribir valor
        inp = find_txtclave(driver, timeout=10)
        if not inp:
            log("❌ Manta: no se encontró el input #txtclave.")
            return None
        try:
            inp.clear()
        except Exception:
            pass
        human_type(inp, valor)
        time.sleep(random.uniform(0.15, 0.35))

        # Clic en Consultar
        btn = find_btn_buscar(driver, timeout=10)
        if not btn:
            log("❌ Manta: no se encontró el botón #btnbuscar_2.")
            return None
        human_click_element(driver, btn)

        # Esperar resultados y capturar
        wait_results(driver, timeout=25)
        base = _safe_name(f"predio_manta_{valor}")
        abs_path = save_fullpage_png(driver, basename=base)
        log(f"📸 Predio Manta: captura final guardada en: {abs_path}")
        return {"screenshot_path": abs_path}

    finally:
        try:
            driver.quit()
        except Exception:
            pass
