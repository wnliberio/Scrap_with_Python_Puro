# core/pages/google_page.py
import time
import random
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.utils.log import log
from core.human import human_type, human_click_element

GOOGLE_URL = "https://www.google.com/search?q=google&sca_esv=cb1e697b99ad7555&rlz=1C1GCEU_esEC1162EC1162&ei=SSTDaNfRH9aJwbkPqp6NyQ0&ved=0ahUKEwiXmsuDutGPAxXWRDABHSpPI9kQ4dUDCBA&uact=5&oq=google&gs_lp=Egxnd3Mtd2l6LXNlcnAiBmdvb2dsZTIWEC4YgAQYsQMY0QMYQxiDARjHARiKBTIQEAAYgAQYsQMYQxiDARiKBTIQEAAYgAQYsQMYQxiDARiKBTINEAAYgAQYsQMYQxiKBTINEAAYgAQYsQMYQxiKBTILEAAYgAQYsQMYgwEyChAAGIAEGEMYigUyDRAAGIAEGLEDGEMYigUyDRAAGIAEGLEDGEMYigUyChAAGIAEGEMYigUyJRAuGIAEGLEDGNEDGEMYgwEYxwEYigUYlwUY3AQY3gQY4ATYAQJI_itQxhtY6ylwAngBkAEAmAF8oAG6BqoBAzAuN7gBA8gBAPgBAZgCCaACigeoAhTCAhkQLhiABBjRAxhDGLQCGMcBGIoFGOoC2AEBwgITEAAYgAQYQxi0AhiKBRjqAtgBAcICEBAAGAMYtAIY6gIYjwHYAQLCAhAQLhgDGLQCGOoCGI8B2AECwgIKEC4YgAQYQxiKBcICDhAAGIAEGLEDGIMBGIoFwgIIEAAYgAQYsQPCAg0QABiABBixAxiDARgKmAMR8QXbPbPduz0shroGBAgBGAe6BgYIAhABGAqSBwMyLjegB8M5sgcDMC43uAfyBsIHBTItNy4yyAdI&sclient=gws-wiz-serp"


def _sleep(a: float, b: float):
    time.sleep(random.uniform(a, b))


def _visible(el) -> bool:
    try:
        return el.is_displayed()
    except Exception:
        return False


def _find_consent_button_here(driver) -> Optional[object]:
    """
    Busca un botón de consentimiento (Aceptar / Rechazar / De acuerdo) en el contexto actual (documento o iframe actual).
    Devuelve el WebElement o None.
    """
    # Candidatos típicos de Google (varían por región/idioma)
    xpaths = [
        # Español
        "//button[.//text()[contains(translate(., 'ACEPTARÉSTOD', 'aceptaréstod'), 'acept')]]",
        "//button[.//text()[contains(translate(., 'RECHAZARTODO', 'rechazartodo'), 'rechaz')]]",
        "//button[.//text()[contains(translate(., 'DEACUERDO', 'deacuerdo'), 'acuerdo')]]",
        "//button[@aria-label and contains(translate(@aria-label,'ACEPTAR','aceptar'),'aceptar')]",
        "//button[@aria-label and contains(translate(@aria-label,'RECHAZAR','rechazar'),'rechazar')]",
        # Portugués / Inglés de respaldo
        "//button[.//text()[contains(translate(., 'ACEITARACEPTARACCEPT', 'aceitaraceptaraccept'), 'accept')]]",
        "//button[.//text()[contains(translate(., 'REJEITARREJECT', 'rejeitarreject'), 'reject')]]",
    ]
    for xp in xpaths:
        try:
            els = driver.find_elements(By.XPATH, xp)
            for el in els:
                if _visible(el):
                    return el
        except Exception:
            continue
    # CSS comunes (cuando usan data-ved o clases de sandwich)
    csss = [
        "button[aria-label*='Aceptar']",
        "button[aria-label*='Rechazar']",
        "button:contains('Aceptar')",
        "button:contains('Rechazar')",
    ]
    for sel in csss:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if _visible(el):
                    return el
        except Exception:
            continue
    return None


def dismiss_consent_if_present(driver, timeout_iframe: int = 6) -> None:
    """
    Cierra el modal/overlay de consentimiento si aparece.
    - Busca primero en el documento principal.
    - Luego intenta en iframes (consent.google).
    - Click humano (pyautogui) y fallback JS.
    Si no aparece, continúa.
    """
    # 0) Intento en documento principal
    try:
        btn = _find_consent_button_here(driver)
        if btn:
            log("ℹ️ Google: botón de consentimiento detectado en documento principal.")
            try:
                human_click_element(driver, btn)
                _sleep(0.4, 0.8)
                return
            except Exception:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    _sleep(0.1, 0.2)
                    driver.execute_script("arguments[0].click();", btn)
                    _sleep(0.3, 0.6)
                    return
                except Exception:
                    pass
    except Exception:
        pass

    # 1) Iframes potenciales
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
    except Exception:
        iframes = []

    for idx, f in enumerate(iframes):
        try:
            src = (f.get_attribute("src") or "").lower()
            name = (f.get_attribute("name") or "").lower()
            id_ = (f.get_attribute("id") or "").lower()
            # Heurística: iframes de consentimiento suelen contener "consent"
            if ("consent" in src) or ("consent" in name) or ("consent" in id_) or True:
                driver.switch_to.frame(f)
                _sleep(0.2, 0.4)
                btn = _find_consent_button_here(driver)
                if btn and _visible(btn):
                    log(f"ℹ️ Google: botón de consentimiento detectado en iframe {idx}.")
                    try:
                        human_click_element(driver, btn)
                        _sleep(0.4, 0.8)
                        driver.switch_to.default_content()
                        return
                    except Exception:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                            _sleep(0.1, 0.2)
                            driver.execute_script("arguments[0].click();", btn)
                            _sleep(0.3, 0.6)
                            driver.switch_to.default_content()
                            return
                        except Exception:
                            pass
                driver.switch_to.default_content()
        except Exception:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

    # 2) Como último recurso, intenta ocultar overlays comunes
    try:
        driver.switch_to.default_content()
        driver.execute_script("""
          // Ocultar overlays comunes de consentimiento si existen
          const ids = ['CXQnmb', 'L2AGLb', 'cnsw', 'lb', 'gb', 'gn', 'fbar'];
          ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.style.display = 'none'; }
          });
          // También probamos con role=dialog
          document.querySelectorAll('[role=dialog]').forEach(d => d.style.display='none');
        """)
        _sleep(0.1, 0.2)
    except Exception:
        pass


def find_search_input(driver, timeout: int = 15):
    """
    Ubica el input/textarea de búsqueda en la home de Google.
    Orden de preferencia:
      - #APjFqb (textarea actual)
      - name="q"
      - cualquier input/textarea con name="q"
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "APjFqb"))
        )
    except TimeoutException:
        pass

    # Fallbacks
    candidates = []
    try:
        candidates += driver.find_elements(By.NAME, "q")
    except Exception:
        pass
    try:
        candidates += driver.find_elements(By.CSS_SELECTOR, "textarea[name='q'], input[name='q']")
    except Exception:
        pass

    for el in candidates:
        try:
            if _visible(el):
                return el
        except Exception:
            continue

    return None


def wait_results_ready(driver, timeout: int = 30) -> bool:
    """
    Espera a que se cargue la SERP con resultados:
      - #search visible
      - o #result-stats / elementos típicos de resultados
    """
    end = time.time() + timeout
    while time.time() < end:
        try:
            # ¿contenedor principal?
            conts = driver.find_elements(By.CSS_SELECTOR, "#search, div#search")
            for c in conts:
                if _visible(c):
                    _sleep(0.4, 0.8)
                    return True
            # ¿estadísticas/indicadores?
            stats = driver.find_elements(By.ID, "result-stats")
            for s in stats:
                if _visible(s):
                    _sleep(0.3, 0.6)
                    return True
            # ¿algún bloque típico?
            blocks = driver.find_elements(By.CSS_SELECTOR, "div.MjjYud, div#center_col, div.g")
            for b in blocks:
                if _visible(b):
                    _sleep(0.3, 0.6)
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False
