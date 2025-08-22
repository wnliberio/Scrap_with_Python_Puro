# core/pages/antecedentes_page.py
import time
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from ..utils.log import log
from ..config import RESULTS_TIMEOUT

# -------------------------------
# BANNERS / MODALES
# -------------------------------

def accept_cookies_if_present(driver, timeout: int = 6) -> bool:
    """
    Acepta el banner de cookies/privacidad (botón 'Aceptar!') si está presente.
    Ejemplos:
      <a class="cc-btn cc-dismiss">Aceptar!</a>
    """
    end = time.time() + timeout
    clicked = False

    while time.time() < end:
        try:
            # CSS directo
            btns = driver.find_elements(By.CSS_SELECTOR, "a.cc-btn.cc-dismiss")
            btns += driver.find_elements(By.XPATH, "//a[contains(@class,'cc-dismiss')]")
            # por texto visible 'Aceptar!'
            btns += driver.find_elements(By.XPATH, "//a[normalize-space()='Aceptar!' or contains(normalize-space(.),'Aceptar')]")
            for b in btns:
                try:
                    if b.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                        time.sleep(0.2)
                        b.click()
                        clicked = True
                        log("✅ Cookies/Privacidad: clic en 'Aceptar!'")
                        time.sleep(0.4)
                        return True
                except Exception:
                    continue

            # Contenedor general (fallback) – por si el botón está cubierto
            conts = driver.find_elements(By.XPATH, "/html/body/div[1]/div")
            for c in conts:
                try:
                    if c.is_displayed():
                        driver.execute_script("arguments[0].click();", c)
                        clicked = True
                        log("✅ Cookies/Privacidad: clic en contenedor (fallback).")
                        time.sleep(0.4)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(0.25)

    if not clicked:
        log("ℹ️ Cookies/Privacidad: banner no presente.")
    return False


def accept_terms_if_present(driver, timeout: int = 8) -> bool:
    """
    Acepta el modal de 'Términos y Condiciones' si aparece.
    Busca botones 'Aceptar' en diálogos jQuery UI u otros.
    """
    end = time.time() + timeout
    while time.time() < end:
        try:
            # Botón típico jQuery UI en footer de diálogos
            btns = driver.find_elements(By.XPATH,
                "//div[contains(@class,'ui-dialog')]//button[.//span[normalize-space()='Aceptar']]"
            )
            # O cualquier botón con texto 'Aceptar'
            btns += driver.find_elements(By.XPATH, "//button[normalize-space()='Aceptar']")
            # Ruta proporcionada por el usuario (por si aparece exactamente así)
            btns += driver.find_elements(By.XPATH, "/html/body/div[6]/div[11]/button[2]")

            for b in btns:
                try:
                    if b.is_displayed() and b.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                        time.sleep(0.2)
                        b.click()
                        log("✅ Términos y Condiciones: aceptado.")
                        time.sleep(0.5)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(0.25)

    log("ℹ️ Términos y Condiciones: modal no presente.")
    return False


# -------------------------------
# hCaptcha
# -------------------------------

def click_hcaptcha_checkbox_iframe(driver, timeout: int = 12) -> bool:
    """
    Intenta clicar el checkbox de hCaptcha dentro de su iframe.
    NO resuelve desafíos gráficos; si aparecen, el flujo continuará por resolución manual.
    Retorna True si logramos hacer el clic al checkbox.
    """
    end = time.time() + timeout
    tried = False
    while time.time() < end:
        try:
            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='hcaptcha.com'], iframe[title*='hCaptcha']")
            for ifr in iframes:
                if not ifr.is_displayed():
                    continue
                driver.switch_to.default_content()
                driver.switch_to.frame(ifr)
                time.sleep(0.3)

                # El checkbox suele tener id="checkbox"
                elems = driver.find_elements(By.XPATH, "//*[@id='checkbox']") or \
                        driver.find_elements(By.CSS_SELECTOR, "#checkbox")
                if elems:
                    tried = True
                    cb = elems[0]
                    try:
                        ActionChains(driver).move_to_element(cb).pause(0.2).click().perform()
                    except Exception:
                        driver.execute_script("arguments[0].click();", cb)
                    log("✅ hCaptcha: clic en checkbox.")
                    driver.switch_to.default_content()
                    return True
            driver.switch_to.default_content()
        except Exception:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
        time.sleep(0.3)

    if not tried:
        log("ℹ️ hCaptcha: iframe/checkbox no visible (quizá no aparece).")
    else:
        log("⚠️ hCaptcha: no se pudo clicar el checkbox (posible desafío).")
    driver.switch_to.default_content()
    return False


# -------------------------------
# Selectores del flujo
# -------------------------------

def find_ci_input(driver) -> Optional[object]:
    try:
        el = driver.find_element(By.CSS_SELECTOR, "#txtCi")
        if el.is_displayed():
            return el
    except Exception:
        pass
    try:
        el = driver.find_element(By.XPATH, "//*[@id='txtCi']")
        if el.is_displayed():
            return el
    except Exception:
        pass
    return None


def find_btn_siguiente(driver) -> Optional[object]:
    # Botón inicial 'Siguiente'
    candidates = []
    candidates += driver.find_elements(By.CSS_SELECTOR, "#btnSig1")
    candidates += driver.find_elements(By.XPATH, "//*[@id='btnSig1']")
    # fallback por texto
    candidates += driver.find_elements(By.XPATH, "//button[.//span[normalize-space()='Siguiente'] or normalize-space()='Siguiente']")
    for b in candidates:
        try:
            if b.is_displayed() and b.is_enabled():
                return b
        except Exception:
            continue
    return None


def wait_overlay_please_wait(driver, timeout: int = 25) -> None:
    """
    Espera a que el overlay 'Por favor espere' aparezca y desaparezca.
    Si no aparece, retorna sin bloquear.
    """
    def any_wait_visible(drv):
        try:
            # Busca cualquier nodo con ese texto en pantalla
            txt = (drv.execute_script("return document.body.innerText||''") or "").lower()
            return "por favor espere" in txt
        except Exception:
            return False

    # Espera breve a que aparezca
    t0 = time.time()
    while time.time() - t0 < min(6, timeout/2):
        if any_wait_visible(driver):
            break
        time.sleep(0.25)

    # Si apareció, esperar a que se vaya
    t1 = time.time()
    while time.time() - t1 < timeout:
        if not any_wait_visible(driver):
            return
        time.sleep(0.4)


def find_textarea_motivo(driver) -> Optional[object]:
    try:
        el = driver.find_element(By.CSS_SELECTOR, "#txtMotivo")
        if el.is_displayed():
            return el
    except Exception:
        pass
    try:
        el = driver.find_element(By.XPATH, "//*[@id='txtMotivo']")
        if el.is_displayed():
            return el
    except Exception:
        pass
    return None


def find_btn_open(driver) -> Optional[object]:
    # 'Visualizar Certificado'
    candidates = []
    candidates += driver.find_elements(By.CSS_SELECTOR, "#btnOpen")
    candidates += driver.find_elements(By.XPATH, "//*[@id='btnOpen']")
    # fallback por texto
    candidates += driver.find_elements(By.XPATH, "//button[.//span[normalize-space()='Visualizar Certificado'] or normalize-space()='Visualizar Certificado']")
    for b in candidates:
        try:
            if b.is_displayed() and b.is_enabled():
                return b
        except Exception:
            continue
    return None


def maybe_btn_siguiente(driver) -> Optional[object]:
    """
    Por si después del motivo hay otro 'Siguiente' antes de 'Visualizar Certificado'.
    """
    candidates = driver.find_elements(By.XPATH, "//button[.//span[normalize-space()='Siguiente'] or normalize-space()='Siguiente']")
    for b in candidates:
        try:
            if b.is_displayed() and b.is_enabled():
                return b
        except Exception:
            continue
    return None


def switch_to_new_tab(driver, timeout: int = 15) -> bool:
    """
    Cambia al último handle si se abre una nueva pestaña.
    """
    t0 = time.time()
    while time.time() - t0 < timeout:
        handles = driver.window_handles
        if len(handles) > 1:
            driver.switch_to.window(handles[-1])
            time.sleep(0.5)
            return True
        time.sleep(0.3)
    return False


def wait_cert_loaded(driver, timeout: int = RESULTS_TIMEOUT) -> bool:
    """
    Espera a que la pestaña del certificado cargue.
    Criterios:
      - URL contiene 'certificado.php'
      - O aparece texto 'CERTIFICADO DE ANTECEDENTES PENALES'
      - O hay <object>/<embed> visibles (PDF/HTML)
    """
    try:
        WebDriverWait(driver, timeout).until(lambda d: _cert_ready(d))
        time.sleep(0.6)
        return True
    except TimeoutException:
        return False


def _cert_ready(drv) -> bool:
    try:
        url = drv.current_url or ""
        if "certificado.php" in url:
            return True
    except Exception:
        pass
    try:
        txt = (drv.execute_script("return document.body.innerText||''") or "")
        if "CERTIFICADO DE ANTECEDENTES PENALES" in txt.upper():
            return True
    except Exception:
        pass
    try:
        objs = drv.find_elements(By.TAG_NAME, "object") + drv.find_elements(By.TAG_NAME, "embed") + drv.find_elements(By.TAG_NAME, "iframe")
        for o in objs:
            try:
                if o.is_displayed():
                    rect = drv.execute_script("var r=arguments[0].getBoundingClientRect();return {w:r.width,h:r.height}", o)
                    if rect and rect.get("w", 0) > 200 and rect.get("h", 0) > 200:
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False
