import time, random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from ..config import RESULTS_TIMEOUT
from ..human import human_click_element, get_element_screen_center
from ..utils.log import log

def find_ruc_input(driver):
    candidates = []
    candidates += driver.find_elements(By.XPATH, "//input[@maxlength='13']")
    candidates += driver.find_elements(By.XPATH, "//input[contains(translate(@name,'RUC','ruc'),'ruc')]")
    candidates += driver.find_elements(By.XPATH, "//input[contains(translate(@id,'RUC','ruc'),'ruc')]")
    if not candidates:
        candidates = [el for el in driver.find_elements(By.XPATH, "//input[@type='text' or @type='search']") if el.is_displayed()]
    if candidates:
        return candidates[0]
    return None

def find_consultar_button(driver, timeout=20):
    waits = WebDriverWait(driver, timeout, poll_frequency=0.25)
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    basic_candidates = [
        (By.XPATH, "//*[@id='sribody']//button[contains(@class,'cyan-btn') and .//span[normalize-space()='Consultar']]"),
        (By.XPATH, "//button[.//span[normalize-space()='Consultar']]"),
        (By.XPATH, "//*[@id='sribody']//button[contains(@class,'cyan-btn')]"),
        (By.CSS_SELECTOR, "#sribody button.cyan-btn.ui-button"),
        (By.XPATH, "//*[@id='sribody']/sri-root/div/div[2]/div/div/sri-consulta-ruc-web-app/div/sri-ruta-ruc/div[2]/div[1]/div[6]/div[2]/div/div[2]/div/button"),
    ]

    try:
        waits.until(EC.presence_of_element_located((By.CSS_SELECTOR, "sri-consulta-ruc-web-app")))
    except TimeoutException:
        pass

    found_visible = []
    for by, sel in basic_candidates:
        try:
            elems = driver.find_elements(by, sel)
            for e in elems:
                try:
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
        log(f"🔎 Consultar: visibles via selectores clásicos = {len(found_visible)}")
        return found_visible[0]

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
                        log("🔎 Consultar: encontrado via Shadow DOM")
                        return btn
                except Exception:
                    return btn
        except Exception as e:
            log(f"ShadowDOM search error: {e}")
        time.sleep(0.25)

    log("🔎 Consultar: no se encontró ni con selectores clásicos ni via Shadow DOM")
    return None

def prepare_for_captcha(driver, zoom=1.2):
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    try:
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/bframe']"))
        )
    except TimeoutException:
        try:
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha']"))
            )
        except TimeoutException:
            log("⚠️ No se encontró iframe de reCAPTCHA para centrar/resaltar.")
            return

    try:
        driver.execute_script("""
            arguments[0].scrollIntoView({block:'center'});
            arguments[0].style.outline = '3px solid #ff5252';
            document.body.style.zoom = arguments[1];
        """, iframe, str(zoom))
    except Exception as e:
        log(f"prepare_for_captcha: no se pudo aplicar outline/zoom: {e}")

    try:
        x, y = get_element_screen_center(driver, iframe)
        import pyautogui
        pyautogui.moveTo(x, y-120, duration=0.4)
    except Exception as e:
        log(f"prepare_for_captcha: no se pudo mover el cursor cerca: {e}")

def wait_for_results(driver) -> bool:
    try:
        container_xpaths = [
            "//div[contains(@class,'resultado') or contains(@id,'resultado')]",
            "//table[contains(@class,'tabla') or contains(@id,'tblResultado')]",
            "//div[contains(@class,'panel-body') and string-length(normalize-space(.))>50]",
            "//sri-mostrar-contribuyente",
        ]
        WebDriverWait(driver, RESULTS_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, '|'.join(container_xpaths)))
        )
        time.sleep(1.0)
        return True
    except TimeoutException:
        return False
