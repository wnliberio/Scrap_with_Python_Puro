# core/pages/mercado_valores_page.py
import time
import random
from typing import Optional, List

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from ..utils.log import log

MERCADO_VALORES_URL = (
    "https://appscvsgen.supercias.gob.ec/consultaCompanias/mercadoValores/busquedaEntesMv.jsf"
)

# -------- utilidades pequeñas "humanas" ----------
def _wait(secs: float):
    time.sleep(random.uniform(secs * 0.65, secs * 1.15))


# -------------------- Finders --------------------
def find_param_input(driver, timeout: int = 20):
    """
    Input de búsqueda (mismo id tanto para Identificación como para Nombre):
    #frmBusquedaEntesMv:parametroBusqueda_input
    """
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "frmBusquedaEntesMv:parametroBusqueda_input"))
        )
        return el
    except TimeoutException:
        return None


def select_mode_nombre(driver, timeout: int = 10) -> bool:
    """
    Cambia el radio a 'Nombre'.
    XPath sugerido: //*[@id="frmBusquedaEntesMv:tipoBusqueda"]/tbody/tr/td[2]/div/div[2]/span
    Hacemos el selector un poco más robusto.
    """
    try:
        rb = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="frmBusquedaEntesMv:tipoBusqueda"]//td[2]//div[contains(@class,"ui-radiobutton-box")]',
                )
            )
        )
        try:
            ActionChains(driver).move_to_element(rb).pause(0.15).click().perform()
        except Exception:
            rb.click()
        _wait(0.25)
        return True
    except TimeoutException:
        log("⚠️ No pude encontrar el radio 'Nombre'.")
        return False


def wait_after_enter(driver, timeout: int = 18) -> bool:
    """
    Tras presionar ENTER, esperamos a que:
      - aparezca el captcha, o
      - se hidrate el panel con datos del ente seleccionado.
    """
    end = time.time() + timeout
    while time.time() < end:
        try:
            # 1) ¿Ya está el captcha visible?
            captcha = driver.find_elements(By.ID, "frmBusquedaEntesMv:captchaImage")
            if any(getattr(c, "is_displayed", lambda: False)() for c in captcha):
                return True

            # 2) ¿Texto típico del panel?
            txt = (driver.execute_script("return document.body.innerText||''") or "").lower()
            if "ente de mercado de valores seleccionado" in txt:
                return True
        except Exception:
            pass
        _wait(0.35)
    return False


def _autocomplete_items(driver) -> List:
    """Obtiene los <li> del autocompletar (si existieran)."""
    try:
        panel = driver.find_element(By.ID, "frmBusquedaEntesMv:parametroBusqueda_panel")
        return panel.find_elements(By.CSS_SELECTOR, "ul.ui-autocomplete-items > li")
    except Exception:
        return []


def click_first_autocomplete_if_any(driver) -> bool:
    """
    Algunas veces tras ENTER hay que 'aceptar' el primer ítem sugerido.
    """
    try:
        items = _autocomplete_items(driver)
        if not items:
            return False
        li = items[0]
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", li)
        _wait(0.15)
        try:
            ActionChains(driver).move_to_element(li).pause(0.12).click().perform()
        except Exception:
            li.click()
        _wait(0.25)
        return True
    except Exception:
        return False


def wait_captcha_ready(driver, timeout: int = 18):
    """
    Espera y devuelve el elemento <img> del captcha.
    """
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.ID, "frmBusquedaEntesMv:captchaImage"))
        )
        # Asegurar que esté en viewport
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        except Exception:
            pass
        _wait(0.35)
        return el
    except TimeoutException:
        return None
