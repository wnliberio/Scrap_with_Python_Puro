# flows/antecedentes.py
import time, random
from typing import Optional, Dict

from selenium.webdriver.common.keys import Keys

from core.config import MAX_RETRIES
from core.browser import create_driver
from core.human import human_type, human_click_element
from core.utils.log import log
from core.utils.screenshot import save_fullpage_png
from core.pages.antecedentes_page import (
    accept_cookies_if_present,
    accept_terms_if_present,
    click_hcaptcha_checkbox_iframe,
    find_ci_input, find_btn_siguiente, wait_overlay_please_wait,
    find_textarea_motivo, find_btn_open, maybe_btn_siguiente,
    switch_to_new_tab, wait_cert_loaded
)

ANTE_URL = "https://certificados.ministeriodelinterior.gob.ec/gestorcertificados/antecedentes/"
MOTIVO_DEFAULT = "Debida Diligencia"

def process_antecedentes_once(cedula: str, headless: bool = False) -> Optional[Dict]:
    driver = create_driver(headless=headless)
    try:
        log(f"➡️ Abriendo {ANTE_URL}")
        driver.get(ANTE_URL)
        time.sleep(random.uniform(0.9, 1.6))

        # 1) Cookies/privacidad (puede salir aquí o luego)
        accept_cookies_if_present(driver)

        # 2) hCaptcha: intentar clic checkbox; si hay desafío, luego será manual.
        clicked = click_hcaptcha_checkbox_iframe(driver)
        if not clicked:
            log("ℹ️ hCaptcha: no se pudo clicar o no visible. Si aparece desafío, resuélvelo manualmente.")

        # A veces el banner 'Aceptar!' aparece DESPUÉS del clic al captcha
        accept_cookies_if_present(driver)

        # 3) Términos y Condiciones (modal)
        accept_terms_if_present(driver)

        # 4) Cédula
        ci = find_ci_input(driver)
        if not ci:
            log("⚠️ Antecedentes: input de cédula (#txtCi) no visible aún. Espera breve…")
            time.sleep(2.0)
            ci = find_ci_input(driver)
            if not ci:
                log("❌ Antecedentes: no se encontró #txtCi.")
                return None

        human_type(ci, cedula)
        time.sleep(random.uniform(0.3, 0.7))
        try:
            ci.send_keys(Keys.TAB)
        except Exception:
            pass
        time.sleep(random.uniform(0.2, 0.5))

        # 5) Siguiente
        btn1 = find_btn_siguiente(driver)
        if not btn1:
            log("❌ Antecedentes: no se encontró botón 'Siguiente' inicial.")
            return None
        try:
            human_click_element(driver, btn1)
        except Exception:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn1)
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", btn1)
            except Exception as e2:
                log(f"❌ Antecedentes: JS click 'Siguiente' falló: {e2}")
                return None

        # 6) Espera overlay 'Por favor espere…'
        wait_overlay_please_wait(driver, timeout=30)

        # 7) Motivo
        motivo = find_textarea_motivo(driver)
        if not motivo:
            log("⚠️ Antecedentes: textarea motivo (#txtMotivo) no presente aún. Espera breve…")
            time.sleep(2.0)
            motivo = find_textarea_motivo(driver)
            if not motivo:
                log("❌ Antecedentes: no se encontró #txtMotivo.")
                return None

        human_type(motivo, MOTIVO_DEFAULT)
        time.sleep(random.uniform(0.25, 0.6))
        try:
            motivo.send_keys(Keys.TAB)
        except Exception:
            pass

        # Puede haber otro 'Siguiente' antes del 'Visualizar Certificado'
        btn_next2 = maybe_btn_siguiente(driver)
        if btn_next2:
            try:
                human_click_element(driver, btn_next2)
                wait_overlay_please_wait(driver, timeout=30)
            except Exception:
                pass

        # 8) Visualizar Certificado
        btn_open = find_btn_open(driver)
        if not btn_open:
            log("⚠️ Antecedentes: botón 'Visualizar Certificado' no visible aún. Espera breve…")
            time.sleep(2.0)
            btn_open = find_btn_open(driver)
            if not btn_open:
                log("❌ Antecedentes: no se encontró botón 'Visualizar Certificado'.")
                return None

        try:
            human_click_element(driver, btn_open)
        except Exception:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_open)
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", btn_open)
            except Exception as e2:
                log(f"❌ Antecedentes: JS click 'Visualizar Certificado' falló: {e2}")
                return None

        # 9) Cambiar a la pestaña del certificado
        switched = switch_to_new_tab(driver, timeout=15)
        if not switched:
            log("ℹ️ Antecedentes: no se detectó nueva pestaña; puede haberse abierto en la misma.")

        # 10) Esperar que cargue el certificado
        if not wait_cert_loaded(driver, timeout=40):
            log("⏳ Antecedentes: no se confirmó carga del certificado; se tomará captura igualmente.")

        # 11) Captura final
        abs_path = save_fullpage_png(driver, basename=f"mininter_antecedentes_{cedula}")
        log(f"📸 Antecedentes: captura final guardada en: {abs_path}")
        return {"screenshot_path": abs_path}

    finally:
        try:
            driver.quit()
        except Exception:
            pass


def process_antecedentes(cedula: str, headless: bool = False) -> Optional[Dict]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- Procesando ANTECEDENTES {cedula} (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_antecedentes_once(cedula, headless=headless)
            if data:
                return data
        except Exception as e:
            log(f"❌ Antecedentes: Error en intento {attempt}: {e}")
            time.sleep(min(3 + attempt * 2, 15))
    log(f"🛑 Antecedentes: falló el procesamiento para {cedula} tras {MAX_RETRIES} intentos.")
    return None
