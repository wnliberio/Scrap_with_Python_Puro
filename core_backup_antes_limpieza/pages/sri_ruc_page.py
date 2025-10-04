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

# NUEVA FUNCIÓN: Encontrar y hacer clic en el botón adicional
def find_and_click_detail_button(driver, timeout=20) -> bool:
    """
    Encuentra y hace clic en el botón que muestra los detalles completos del contribuyente.
    XPath: //*[@id="sribody"]/sri-root/div/div[2]/div/div/sri-consulta-ruc-web-app/div/sri-ruta-ruc/div[2]/div[3]/div[1]/div[2]/div/div[4]/button
    """
    try:
        # Intentar con el XPath específico primero
        button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='sribody']/sri-root/div/div[2]/div/div/sri-consulta-ruc-web-app/div/sri-ruta-ruc/div[2]/div[3]/div[1]/div[2]/div/div[4]/button"))
        )
        
        log("🔎 RUC: Botón de detalles(Mostrar establecimientos) encontrado con XPath específico")
        human_click_element(driver, button)
        time.sleep(random.uniform(1.0, 2.0))  # Esperar a que se carguen los detalles
        return True
        
    except TimeoutException:
        # Fallback: buscar botones que puedan mostrar más detalles
        try:
            # Buscar botones con texto que indique "ver más", "detalles", etc.
            fallback_selectors = [
                "//button[contains(text(), 'Ver')]",
                "//button[contains(text(), 'Detalle')]", 
                "//button[contains(text(), 'Más')]",
                "//button[contains(@class, 'btn') and contains(@class, 'cyan')]",
                "//*[@id='sribody']//button[position()>1]"  # segundo botón o posterior
            ]
            
            for selector in fallback_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    for btn in buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            log(f"🔎 RUC: Usando botón fallback: {selector}")
                            human_click_element(driver, btn)
                            time.sleep(random.uniform(1.0, 2.0))
                            return True
                except Exception:
                    continue
                    
            log("⚠️ RUC: No se encontró el botón de detalles, continuando sin hacer clic")
            return False
            
        except Exception as e:
            log(f"⚠️ RUC: Error buscando botón de detalles: {e}")
            return False

# NUEVA FUNCIÓN: Encontrar la sección de datos del contribuyente
def find_contributor_data_section(driver, timeout=15):
    """
    Encuentra el contenedor principal de toda la consulta de RUC.
    Usando el selector más amplio para capturar todo el contenido.
    """
    try:
        # Selector principal - toda la aplicación de consulta RUC
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "sri-consulta-ruc-web-app"))
        )
    except TimeoutException:
        try:
            # Fallback - contenedor de la ruta
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "sri-ruta-ruc"))
            )
        except TimeoutException:
            try:
                # Último fallback - div principal dentro de sri-root
                return WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#sribody sri-root .layout-main"))
                )
            except TimeoutException:
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

def detect_ruc_result_state(driver, timeout: int = 30) -> str:
    """
    Detecta el estado después de hacer la consulta de RUC.
    Retorna:
      - 'results_found' -> hay datos del contribuyente
      - 'no_results'    -> RUC no encontrado/sin resultados
      - 'timeout'       -> no se pudo determinar
    """
    end = time.time() + timeout
    
    while time.time() < end:
        try:
            # Verificar elemento específico del mensaje de error
            error_elements = driver.find_elements(By.CSS_SELECTOR, ".ui-messages-warn, .ui-messages")
            for el in error_elements:
                if el.is_displayed():
                    error_text = (el.text or "").lower()
                    if "no generó resultados" in error_text:
                        return "no_results"
            
            # También verificar por texto en el body
            body_text = (driver.execute_script("return document.body.innerText || ''") or "").lower()
            no_results_indicators = [
                "la búsqueda no generó resultados",
                "no generó resultados"
            ]
            
            if any(indicator in body_text for indicator in no_results_indicators):
                return "no_results"
            
            # Verificar si hay datos del contribuyente (indicadores de éxito)
            success_indicators = [
                "razón social",
                "estado contribuyente",
                "actividad económica",
                "activo"
            ]
            
            if any(indicator in body_text for indicator in success_indicators):
                return "results_found"
            
            # También verificar elementos específicos de resultados
            result_elements = driver.find_elements(By.CSS_SELECTOR, "sri-mostrar-contribuyente")
            if result_elements and any(el.is_displayed() for el in result_elements):
                return "results_found"
            
            time.sleep(0.5)
            
        except Exception:
            time.sleep(0.5)
    
    return "timeout"

def find_no_results_section(driver, timeout: int = 10):
    """
    Encuentra la sección que contiene el mensaje de "sin resultados" usando el selector exacto.
    """
    try:
        # Selector exacto basado en el HTML proporcionado
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-messages-warn.ng-star-inserted"))
        )
    except TimeoutException:
        try:
            # Fallback: cualquier mensaje de warning
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-messages-warn"))
            )
        except TimeoutException:
            try:
                # Fallback más general: cualquier mensaje UI
                return WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-messages"))
                )
            except TimeoutException:
                return None

def find_no_results_section(driver, timeout: int = 10):
    """
    Encuentra la sección que contiene el mensaje de "sin resultados"
    """
    try:
        # Buscar el contenedor con el mensaje de error
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'La búsqueda no generó resultados')]//ancestor::div[contains(@class, 'alert') or contains(@class, 'warning') or position()<=3]"))
        )
    except TimeoutException:
        try:
            # Fallback: buscar cualquier contenedor de alerta/warning
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".alert, .warning, .error, .mensaje"))
            )
        except TimeoutException:
            # Último fallback: el contenedor principal de consulta
            try:
                return WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "sri-consulta-ruc-web-app"))
                )
            except TimeoutException:
                return None