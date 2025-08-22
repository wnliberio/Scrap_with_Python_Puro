# core/pages/sri_deudas_page.py
import time, random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from ..utils.log import log
from ..config import RESULTS_TIMEOUT

def find_ident_input(driver):
    """
    Retorna el input de cédula/RUC (10 a 13 dígitos) de la página de Deudas.
    Selector principal: #busquedaRucId
    """
    try:
        el = driver.find_element(By.CSS_SELECTOR, "#busquedaRucId")
        if el.is_displayed():
            return el
    except Exception:
        pass

    # Fallbacks
    candidates = []
    candidates += driver.find_elements(By.XPATH, "//input[@id='busquedaRucId']")
    candidates += driver.find_elements(By.XPATH, "//input[contains(translate(@name,'RUCID','rucid'),'rucid')]")
    candidates += driver.find_elements(By.XPATH, "//input[@type='text' or @type='search']")
    for el in candidates:
        try:
            if el.is_displayed():
                return el
        except Exception:
            continue
    return None

def find_consultar_button_deudas(driver, timeout=25):
    """
    Ubica el botón 'Consultar' en Deudas.
    Usa XPaths/selector y, si no aparece, busca por Shadow DOM con texto 'Consultar'.
    """
    waits = WebDriverWait(driver, timeout, poll_frequency=0.25)
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    # 1) Candidatos conocidos
    basic_candidates = [
        # el <span> dentro del botón (subimos a <button>)
        (By.XPATH, "//*[@id='sribody']/sri-root/div/div[2]/div/div/sri-consulta-deudas-firmes-impugnadas-web-app/div/sri-ruta-consulta-deudas-firmes-impugnadas/div[1]/div[6]/div[2]/div/div[2]/div[3]/button/span"),
        # el <button> directo
        (By.XPATH, "//*[@id='sribody']/sri-root/div/div[2]/div/div/sri-consulta-deudas-firmes-impugnadas-web-app/div/sri-ruta-consulta-deudas-firmes-impugnadas/div[1]/div[6]/div[2]/div/div[2]/div[3]/button"),
        # selector CSS largo proporcionado
        (By.CSS_SELECTOR, "#sribody > sri-root > div > div.layout-main > div > div > sri-consulta-deudas-firmes-impugnadas-web-app > div > sri-ruta-consulta-deudas-firmes-impugnadas > div.ng-star-inserted > div:nth-child(7) > div.col-sm-6 > div > div:nth-child(2) > div.d-flex.justify-content-center > button > span"),
        # fallback genérico
        (By.XPATH, "//button[.//span[normalize-space()='Consultar']]"),
    ]

    found_visible = []
    for by, sel in basic_candidates:
        try:
            elems = driver.find_elements(by, sel)
            for e in elems:
                try:
                    # si apunta al <span>, subimos al botón
                    if e.tag_name.lower() != "button":
                        try:
                            parent = e.find_element(By.XPATH, "./ancestor::button[1]")
                            if parent:
                                e = parent
                        except Exception:
                            pass
                    if e.is_displayed() and e.is_enabled():
                        found_visible.append(e)
                except Exception:
                    continue
        except Exception:
            continue

    if found_visible:
        log(f"🔎 Deudas: botón visible via selectores directos ({len(found_visible)})")
        return found_visible[0]

    # 2) Búsqueda por Shadow DOM
    deep_js = r"""
    const matchesText = (el) => {
      const t = (el && (el.innerText || el.textContent) || '').trim();
      return /^Consultar$/i.test(t) || /(^|\s)Consultar(\s|$)/i.test(t);
    };
    function closestButton(el) {
      if (!el) return null;
      const b = el.closest ? el.closest('button') : null;
      return b || (el.tagName && el.tagName.toLowerCase() === 'button' ? el : null);
    }
    function walk(root) {
      const btns = root.querySelectorAll('button, .ui-button');
      for (const b of btns) {
        if (matchesText(b)) return closestButton(b) || b;
        const span = b.querySelector('span');
        if (matchesText(span)) return closestButton(span) || b;
      }
      const all = root.querySelectorAll('*');
      for (const el of all) {
        if (matchesText(el)) {
          const b = closestButton(el);
          if (b) return b;
        }
        if (el.shadowRoot) {
          const found = walk(el.shadowRoot);
          if (found) return found;
        }
      }
      return null;
    }
    return walk(document);
    """

    end = time.time() + timeout
    while time.time() < end:
        try:
            btn = driver.execute_script(deep_js)
            if btn:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        log("🔎 Deudas: botón encontrado via Shadow DOM")
                        return btn
                except Exception:
                    return btn
        except Exception as e:
            log(f"ShadowDOM search (Deudas) error: {e}")
        time.sleep(0.25)

    log("🔎 Deudas: botón no encontrado")
    return None

def wait_for_deudas_results(driver, timeout=RESULTS_TIMEOUT) -> bool:
    """
    Espera a que aparezcan resultados/mensajes propios de la consulta de Deudas.
    Es más flexible que el wait genérico del RUC.
    """
    start = time.time()
    try:
        # pequeña espera inicial para que Angular actualice la vista
        time.sleep(1.2)

        def ready(drv):
            # 1) ¿Hay alguna tabla visible (clases comunes)?
            has_table = drv.execute_script("""
                const sel = 'table, .p-datatable, .ui-datatable, .table';
                const el = document.querySelector(sel);
                if (!el) return false;
                const rect = el.getBoundingClientRect();
                return rect.width > 50 && rect.height > 30;
            """)
            if has_table:
                return True

            # 2) ¿Apareció un mensaje típico (sin deudas, etc.)?
            txt = (drv.execute_script("return document.body.innerText || ''") or "").lower()
            consts = [
                "no posee deudas", "no registra deudas", "no existen deudas",
                "deudas firmes", "deudas impugnadas", "resultado", "detalle de deudas"
            ]
            return any(c in txt for c in consts)

        WebDriverWait(driver, timeout, poll_frequency=0.5).until(lambda d: ready(d))
        time.sleep(0.6)  # estabilizar layout
        return True
    except TimeoutException:
        return False
