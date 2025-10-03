"""
Script de prueba independiente para Función Judicial
Incluye integración automática con CapSolver SOLO cuando aparece ventana de imágenes.
- Modo headless opcional
- Simula movimientos humanos
- Flujo: escribir nombre -> clic1 -> clic2 (checkbox) -> detectar ventana imágenes -> resolver SOLO si hay ventana -> clic3 -> analizar resultado
"""

import time
import random
import os
import requests
import traceback
import urllib.parse as up
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ============= CONFIGURACIÓN =============
FUNCION_JUDICIAL_URL = "https://procesosjudiciales.funcionjudicial.gob.ec/busqueda-filtros"
NOMBRE_PRUEBA = "José Adolfo Macías Villamar"
SCREENSHOTS_DIR = Path("screenshots_test")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# ============= CONFIG CAPSOLVER (quemado) ============
# ⚠️ Si prefieres seguridad, carga estas desde variables de entorno
CAPSOLVER_API_KEY = "CAP-E6752C17A4ABA2B00B5CA4709EB0624568BE753E83D3C4885B1AD5F121E7898D"
BURNED_SITEKEY = "6LfjVAcUAAAAANT1V80aWo"
# ====================================================

# CONTROL: usar undetected-chromedriver o Selenium normal
USE_UNDETECTED = True  # Cambiar a False si quieres Selenium normal
HEADLESS_DEFAULT = True  # Cambiar a False para ver la UI por defecto en pruebas

# ============= UTILIDADES =============
def log(mensaje):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {mensaje}")

def wait_random(min_sec=0.5, max_sec=2.0):
    time.sleep(random.uniform(min_sec, max_sec))

def slug(text):
    import re
    return re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '_').lower()

def save_screenshot(driver, nombre_archivo):
    filepath = SCREENSHOTS_DIR / f"{nombre_archivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    try:
        driver.save_screenshot(str(filepath))
        log(f"📸 Screenshot guardado: {filepath}")
        return str(filepath)
    except Exception as e:
        log(f"❌ Error guardando screenshot: {e}")
        return None

# ============= CREAR DRIVER =============
def create_headless_driver(headless=True):
    log("🚀 Creando driver con anti-detección...")
    try:
        if USE_UNDETECTED:
            import undetected_chromedriver as uc
            log("🥷 Usando undetected-chromedriver")
            options = uc.ChromeOptions()
            if headless:
                options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            driver = uc.Chrome(options=options, version_main=None)
            log("✅ Driver undetected creado")
            return driver
    except Exception as e:
        log(f"⚠️ undetected-chromedriver no disponible o falló: {e}")

    # Fallback: Selenium normal con tweaks anti-detección
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(options=options)

    # anti-detección JS tweaks
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'permissions', { get: () => ({ query: () => Promise.resolve({ state: 'granted' }) }) });
                Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['es-ES','es','en-US','en']});
                window.chrome = { runtime: {} };
            '''
        })
    except Exception as e:
        log(f"⚠️ No se pudo aplicar todos los tweaks (está bien): {e}")

    log("✅ Driver Selenium normal creado")
    return driver

# ============= MOVIMIENTOS HUMANOS =============
def random_scroll_smooth(driver, direction='down', distance=None):
    if distance is None:
        distance = random.randint(100, 400)
    distance = distance if direction == 'down' else -abs(distance)
    steps = random.randint(8, 15)
    step_size = distance / steps
    for _ in range(steps):
        driver.execute_script(f"window.scrollBy(0, {step_size});")
        time.sleep(random.uniform(0.02, 0.08))
    correction = random.randint(-20, 20)
    driver.execute_script(f"window.scrollBy(0, {correction});")
    time.sleep(random.uniform(0.1, 0.2))

def move_mouse_in_circle(driver, element, radius=50):
    import math
    log("🔄 Movimiento circular del cursor...")
    actions = ActionChains(driver)
    actions.move_to_element(element).perform()
    points = 8
    for i in range(points):
        angle = (2 * math.pi * i) / points
        offset_x = int(radius * math.cos(angle))
        offset_y = int(radius * math.sin(angle))
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(element, offset_x, offset_y)
        actions.pause(random.uniform(0.05, 0.12))
        actions.perform()
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.pause(random.uniform(0.1, 0.2))
    actions.perform()
    log("✅ Movimiento circular completado")

def move_mouse_zigzag(driver, element, steps=5):
    log("↔️ Movimiento zigzag...")
    actions = ActionChains(driver)
    for i in range(1, steps + 1):
        progress = i / steps
        lateral_offset = random.randint(-30, 30) if i < steps else 0
        vertical_offset = int(-50 * progress)
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(element, lateral_offset, vertical_offset)
        actions.pause(random.uniform(0.05, 0.15))
        actions.perform()
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.pause(random.uniform(0.1, 0.2))
    actions.perform()
    log("✅ Zigzag completado")

def move_mouse_bezier_curve(driver, element, control_points=3):
    import math
    log("📐 Movimiento Bézier...")
    points = []
    for i in range(control_points):
        offset_x = random.randint(-80, 80)
        offset_y = random.randint(-80, 80)
        points.append((offset_x, offset_y))
    points.append((0,0))
    steps = 12
    for step in range(steps):
        t = step / (steps - 1)
        if len(points) >= 3:
            idx = int(t * (len(points) - 1))
            if idx >= len(points) - 1:
                offset_x, offset_y = points[-1]
            else:
                p1 = points[idx]; p2 = points[idx+1]; local_t = (t * (len(points) - 1)) - idx
                offset_x = p1[0] + (p2[0] - p1[0]) * local_t
                offset_y = p1[1] + (p2[1] - p1[1]) * local_t
        else:
            offset_x, offset_y = 0,0
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(element, int(offset_x), int(offset_y))
        actions.pause(random.uniform(0.04, 0.1))
        actions.perform()
    log("✅ Bézier completado")

def human_like_scroll_and_read(driver):
    log("👁️ Simulando lectura humana...")
    random_scroll_smooth(driver, 'down', random.randint(150, 300))
    wait_random(0.5, 1.2)
    random_scroll_smooth(driver, 'up', random.randint(50, 150))
    wait_random(0.3, 0.8)
    random_scroll_smooth(driver, 'down', random.randint(100, 250))
    wait_random(0.4, 0.9)
    driver.execute_script("window.scrollTo(0, 0);")
    wait_random(0.3, 0.6)
    log("✅ Lectura simulada")

# ============= DETECCIÓN Y BÚSQUEDA DE ELEMENTOS =============
def find_name_input(driver, timeout=15):
    log("🔍 Buscando campo de nombres...")
    try:
        element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "mat-input-4")))
        log("✅ Campo de nombres encontrado: #mat-input-4")
        return element
    except TimeoutException:
        log("⚠️ No se encontró por ID, intentando XPath...")
        try:
            element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="mat-input-4"]')))
            log("✅ Campo de nombres encontrado: XPath")
            return element
        except TimeoutException:
            log("❌ No se pudo encontrar el campo de nombres")
            return None

def find_search_button(driver, timeout=15):
    log("🔍 Buscando botón de búsqueda...")
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.boton-buscar.mdc-button.mdc-button--raised.mat-mdc-raised-button.mat-accent"))
        )
        log("✅ Botón de búsqueda encontrado")
        return element
    except TimeoutException:
        log("⚠️ No se encontró el botón con CSS, intentando XPath...")
        try:
            element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'boton-buscar')]")))
            log("✅ Botón de búsqueda encontrado: XPath")
            return element
        except TimeoutException:
            log("❌ No se pudo encontrar el botón de búsqueda")
            return None

# ============= ESCRITURA HUMANA ============
def human_type_selenium(driver, element, text, base_delay=0.15):
    log(f"✏️ Escribiendo: {text}")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
    wait_random(0.5, 1.0)
    try:
        element.clear()
    except:
        pass
    wait_random(0.5, 1.0)
    try:
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(element, random.randint(-10, 10), random.randint(-5, 5))
        actions.pause(random.uniform(0.2, 0.4))
        actions.move_to_element(element)
        actions.pause(random.uniform(0.1, 0.3))
        actions.click()
        actions.perform()
    except:
        try:
            element.click()
        except:
            pass
    wait_random(0.3, 0.6)
    for i, char in enumerate(text):
        try:
            element.send_keys(char)
        except:
            pass
        delay = max(0.08, random.gauss(base_delay, base_delay * 0.4))
        time.sleep(delay)
        if char in ' ':
            time.sleep(random.uniform(0.15, 0.35))
        elif char in ',.;:':
            time.sleep(random.uniform(0.2, 0.4))
        if i > 0 and i % random.randint(5, 8) == 0:
            time.sleep(random.uniform(0.15, 0.35))
            if random.random() < 0.3:
                try:
                    actions = ActionChains(driver)
                    actions.move_by_offset(random.randint(-20, 20), random.randint(-20, 20))
                    actions.pause(0.1)
                    actions.perform()
                    actions = ActionChains(driver)
                    actions.move_to_element(element)
                    actions.perform()
                except:
                    pass
    log(f"✅ Texto escrito ({len(text)} caracteres)")

def selenium_click_element(driver, element, use_human_movement=True):
    log("🖱️ Preparando click con movimientos humanos...")
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
        wait_random(0.8, 1.5)
        random_scroll_smooth(driver, random.choice(['up', 'down']), random.randint(20, 80))
        wait_random(0.3, 0.7)
        if use_human_movement:
            movement_type = random.choice(['zigzag', 'circle', 'bezier', 'direct'])
            if movement_type == 'zigzag':
                move_mouse_zigzag(driver, element, steps=random.randint(4, 7))
            elif movement_type == 'circle':
                move_mouse_in_circle(driver, element, radius=random.randint(30, 60))
            elif movement_type == 'bezier':
                move_mouse_bezier_curve(driver, element, control_points=random.randint(2, 4))
            else:
                actions = ActionChains(driver)
                actions.move_to_element_with_offset(element, random.randint(-15, 15), random.randint(-10, 10))
                actions.pause(random.uniform(0.2, 0.4))
                actions.move_to_element(element)
                actions.pause(random.uniform(0.2, 0.5))
                actions.perform()
        else:
            actions = ActionChains(driver)
            actions.move_to_element(element)
            actions.pause(random.uniform(0.3, 0.7))
            actions.perform()
        wait_random(0.4, 0.9)
        actions = ActionChains(driver)
        actions.click()
        actions.pause(random.uniform(0.08, 0.18))
        actions.perform()
        log("✅ Click exitoso")
        return True
    except Exception as e:
        log(f"⚠️ Movimientos humanos fallaron: {e}, intentando JS click...")
        try:
            wait_random(0.3, 0.6)
            driver.execute_script("arguments[0].click();", element)
            log("✅ Click exitoso (JS fallback)")
            return True
        except Exception as e2:
            log(f"❌ Click JS también falló: {e2}")
            return False

# ============= DETECCIÓN DE RESULTADOS ============
def detect_no_results_modal(driver, timeout=5):
    log("🔍 Verificando modal 'sin resultados'...")
    try:
        no_results_selectors = [
            "//div[contains(text(), 'La consulta no devolvió resultados')]",
            "//div[contains(text(), 'La consulta no devolvió resultados. Cerrar')]",
            "//div[starts-with(@id, 'mat-snack-bar-container-live')]/div/simple-snack-bar",
            "//div[starts-with(@id, 'mat-snack-bar-container-live')]//div[contains(@class, 'mat-mdc-snack-bar-label')]"
        ]
        for selector in no_results_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        log(f"✅ Detectado modal 'sin resultados': {text}")
                        return True
            except:
                continue
        try:
            result = driver.execute_script("""
                const text = document.body.innerText.toLowerCase();
                return text.includes('la consulta no devolvió resultados') || 
                       text.includes('la consulta no devolvió resultados. cerrar');
            """)
            if result:
                log("✅ Detectado 'sin resultados' por contenido de texto")
                return True
        except:
            pass
        log("ℹ️ No se detectó modal 'sin resultados'")
        return False
    except Exception as e:
        log(f"⚠️ Error detectando modal sin resultados: {e}")
        return False

def detect_results_loaded(driver, timeout=10):
    log("🔍 Verificando si hay resultados cargados...")
    try:
        wait_random(2.0, 3.0)
        results_selectors = [
            "table tbody tr",
            "mat-row",
            ".mat-mdc-row",
            "div.result-item",
            "div.resultado",
            ".list-item",
            "tr[role='row']"
        ]
        for selector in results_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                visible_elements = [e for e in elements if e.is_displayed()]
                if len(visible_elements) > 0:
                    log(f"✅ Detectados {len(visible_elements)} resultados con selector: {selector}")
                    return True
            except:
                continue
        try:
            results_container = driver.find_element(By.CSS_SELECTOR,
                "body > app-root > app-expel-listado-juicios > expel-sidenav > mat-sidenav-container > mat-sidenav-content > section"
            )
            if results_container.is_displayed():
                content_height = driver.execute_script("return arguments[0].scrollHeight;", results_container)
                if content_height > 200:
                    log(f"✅ Contenedor de resultados detectado (altura: {content_height}px)")
                    return True
        except:
            pass
        log("ℹ️ No se detectaron resultados cargados")
        return False
    except Exception as e:
        log(f"⚠️ Error detectando resultados: {e}")
        return False

# ============= DETECCIÓN DE RECAPTCHA (NUEVO - MEJORADO) ============
def detectar_recaptcha_iframe(driver):
    """Detecta iframes de reCAPTCHA y extrae el sitekey"""
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for f in iframes:
            src = f.get_attribute("src") or ""
            if "recaptcha" in src or "google.com/recaptcha" in src:
                q = up.urlparse(src).query
                kv = dict(up.parse_qsl(q))
                k = kv.get("k")
                return True, k, driver.current_url
    except Exception as e:
        log(f"⚠️ Error detectando iframe recaptcha: {e}")
    return False, None, driver.current_url

def detectar_ventana_imagenes_recaptcha(driver, timeout=5):
    """
    🎯 FUNCIÓN CLAVE: Detecta si apareció la ventana modal con el desafío de IMÁGENES del reCAPTCHA.
    
    Esta ventana aparece después de hacer clic en el checkbox "I'm not a robot"
    cuando Google decide que necesita verificación adicional mediante imágenes
    (semáforos, autos, bicicletas, puentes, etc.)
    
    Retorna:
        True: Si detectó la ventana de imágenes (USAR CAPSOLVER)
        False: Si NO apareció ventana (checkbox se resolvió automáticamente)
    """
    log("🔍 Detectando ventana modal de imágenes del reCAPTCHA...")
    try:
        # Esperar un poco para que la ventana aparezca si va a aparecer
        time.sleep(1.5)
        
        # ===== MÉTODO 1: Buscar iframe del desafío de imágenes (bframe) =====
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                src = iframe.get_attribute("src") or ""
                # El iframe del desafío de imágenes contiene "api2/bframe" o "recaptcha/api2/bframe"
                if ("bframe" in src and "recaptcha" in src) or "api2/bframe" in src:
                    # Verificar si el iframe es visible
                    if iframe.is_displayed():
                        log(f"✅ Iframe de desafío de imágenes detectado: {src[:80]}...")
                        return True
            except:
                continue
        
        # ===== MÉTODO 2: Buscar el contenedor de selección de imágenes directamente =====
        selectores_ventana_imagenes = [
            "div.rc-imageselect",  # Contenedor principal del desafío de imágenes
            "div.rc-imageselect-challenge",  # Contenedor del desafío
            "div.rc-imageselect-target",  # Target de selección
            "table.rc-imageselect-table-33",  # Tabla 3x3 de imágenes
            "table.rc-imageselect-table-44",  # Tabla 4x4 de imágenes
            "div.rc-imageselect-incorrect-response",  # Mensaje de error
            "div.rc-imageselect-desc",  # Descripción del desafío
            "div.rc-imageselect-instructions"  # Instrucciones
        ]
        
        for selector in selectores_ventana_imagenes:
            try:
                elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                for elemento in elementos:
                    if elemento.is_displayed():
                        log(f"✅ Elemento de ventana de imágenes detectado: {selector}")
                        return True
            except:
                continue
        
        # ===== MÉTODO 3: Buscar por XPath elementos específicos del desafío =====
        xpaths_ventana = [
            "//div[contains(@class, 'rc-imageselect')]",
            "//div[contains(@class, 'rc-imageselect-challenge')]",
            "//strong[contains(text(), 'Select all images') or contains(text(), 'Selecciona todas las imágenes')]"
        ]
        
        for xpath in xpaths_ventana:
            try:
                elementos = driver.find_elements(By.XPATH, xpath)
                for elemento in elementos:
                    if elemento.is_displayed():
                        log(f"✅ Ventana de imágenes detectada por XPath")
                        return True
            except:
                continue
        
        # ===== MÉTODO 4: Verificar en el DOM completo con JavaScript =====
        try:
            resultado = driver.execute_script("""
                // Buscar elementos visibles que indiquen el desafío de imágenes
                const imageSelectDivs = document.querySelectorAll('div[class*="rc-imageselect"]');
                for (let div of imageSelectDivs) {
                    const style = window.getComputedStyle(div);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        return true;
                    }
                }
                
                // Buscar iframes del desafío
                const iframes = document.querySelectorAll('iframe');
                for (let iframe of iframes) {
                    const src = iframe.src || '';
                    if ((src.includes('bframe') && src.includes('recaptcha')) || src.includes('api2/bframe')) {
                        const style = window.getComputedStyle(iframe);
                        if (style.display !== 'none' && style.visibility !== 'hidden') {
                            return true;
                        }
                    }
                }
                
                return false;
            """)
            
            if resultado:
                log("✅ Ventana de imágenes detectada por JavaScript")
                return True
        except Exception as e:
            log(f"⚠️ Error en detección JavaScript: {e}")
        
        log("ℹ️ No se detectó ventana de imágenes - el checkbox se resolvió automáticamente")
        return False
        
    except Exception as e:
        log(f"⚠️ Error en detección de ventana de imágenes: {e}")
        traceback.print_exc()
        return False

# ============= CAPSOLVER: crear tarea, obtener resultado, inyectar token ============
def crear_tarea_capsolver(site_url, site_key=BURNED_SITEKEY, api_key=CAPSOLVER_API_KEY, timeout=30):
    log(f"🔁 Creando tarea CapSolver para sitekey={site_key} en {site_url} ...")
    payload = {
        "clientKey": api_key,
        "task": {
            "type": "NoCaptchaTaskProxyless",
            "websiteURL": site_url,
            "websiteKey": site_key
        }
    }
    r = requests.post("https://api.capsolver.com/createTask", json=payload, timeout=timeout)
    j = r.json()
    if j.get("errorId", 0) != 0:
        raise Exception(f"Error creando tarea CapSolver: {j}")
    task_id = j.get("taskId")
    log(f"✅ Tarea creada en CapSolver: {task_id}")
    return task_id

def obtener_resultado_capsolver(task_id, api_key=CAPSOLVER_API_KEY, wait_interval=3, max_wait_s=180):
    log(f"⏳ Esperando resultado CapSolver para task {task_id} ...")
    start = time.time()
    while time.time() - start < max_wait_s:
        r = requests.post("https://api.capsolver.com/getTaskResult", json={"clientKey": api_key, "taskId": task_id}, timeout=30)
        j = r.json()
        if j.get("status") == "ready":
            token = j["solution"]["gRecaptchaResponse"]
            log("✅ CapSolver devolvió token (len=%d)" % len(token))
            return token
        if j.get("errorId", 0) != 0:
            raise Exception(f"Error en getTaskResult: {j}")
        log("⏳ procesando... esperando %ds" % wait_interval)
        time.sleep(wait_interval)
    raise TimeoutError("Timeout esperando solución de CapSolver")

def inyectar_token_en_pagina(driver, token):
    log("🔧 Inyectando token en la página...")
    js = """
    (function(token){
      var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
      var padre = document.querySelector('form') || document.body;
      if(!textarea){
        textarea = document.createElement('textarea');
        textarea.name = 'g-recaptcha-response';
        textarea.style.display = 'none';
        padre.appendChild(textarea);
      }
      textarea.value = token;
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
      textarea.dispatchEvent(new Event('change', { bubbles: true }));
    })(arguments[0]);
    """
    driver.execute_script(js, token)
    log("✅ Token inyectado en textarea[name='g-recaptcha-response']")

# ============= PROCESO PRINCIPAL ============
def test_funcion_judicial_with_capsolver(apellidos_nombres, headless=True):
    driver = None
    try:
        log("=" * 80)
        log("🏛️ INICIANDO PRUEBA FUNCIÓN JUDICIAL (con CapSolver INTELIGENTE)")
        log(f"📝 Nombre a buscar: {apellidos_nombres}")
        log(f"🎭 Modo headless: {headless}")
        log(f"🧠 CapSolver se usará SOLO si aparece ventana de imágenes")
        log("=" * 80)

        # Crear driver
        driver = create_headless_driver(headless=headless)

        # Ir a la página
        log(f"🌐 Navegando a: {FUNCION_JUDICIAL_URL}")
        driver.get(FUNCION_JUDICIAL_URL)
        wait_random(3.0, 5.0)

        # Screenshot inicial
        save_screenshot(driver, f"01_pagina_inicial_{slug(apellidos_nombres)}")

        # Simular lectura
        human_like_scroll_and_read(driver)

        # Encontrar campo nombre
        name_input = find_name_input(driver)
        if not name_input:
            log("❌ No se encontró el campo de nombres")
            return None

        # Movimiento hacia el campo
        try:
            move_mouse_in_circle(driver, name_input, radius=40)
        except Exception as e:
            log(f"⚠️ Movimiento circular falló: {e}")

        wait_random(0.5, 1.0)

        # Escribir
        human_type_selenium(driver, name_input, apellidos_nombres)
        wait_random(1.0, 2.0)

        # Screenshot después de escribir
        save_screenshot(driver, f"02_despues_escribir_{slug(apellidos_nombres)}")

        # Buscar botón
        search_btn = find_search_button(driver)
        if not search_btn:
            log("❌ No se encontró el botón de búsqueda")
            return None

        # Secuencia de clics
        log("🔍 Iniciando secuencia de clics especial...")
        try:
            move_mouse_zigzag(driver, search_btn, steps=random.randint(5, 7))
        except Exception as e:
            log(f"⚠️ Movimiento zigzag falló: {e}")
        wait_random(0.5, 1.0)

        # ===== CLIC #1: En botón BUSCAR =====
        log("🖱️ CLIC #1: En botón BUSCAR")
        if not selenium_click_element(driver, search_btn, use_human_movement=True):
            log("❌ Falló clic #1")
            return None
        wait_random(1.5, 2.5)
        save_screenshot(driver, f"03_despues_clic1_{slug(apellidos_nombres)}")
        random_scroll_smooth(driver, random.choice(['up', 'down']), random.randint(40, 100))
        wait_random(0.5, 1.0)

        # ===== CLIC #2: En el CHECKBOX del reCAPTCHA (75px arriba) =====
        log("🖱️ CLIC #2: Preparando click en checkbox reCAPTCHA (75px arriba del botón)")
        log("    ℹ️ Este clic activa el checkbox 'I'm not a robot'")
        wait_random(1.0, 2.0)
        try:
            rect_info = driver.execute_script("""
                var rect = arguments[0].getBoundingClientRect();
                return {
                    left: rect.left,
                    top: rect.top,
                    width: rect.width,
                    height: rect.height,
                    centerX: rect.left + rect.width/2,
                    centerY: rect.top + rect.height/2
                };
            """, search_btn)
            click_x = rect_info['centerX']
            click_y = rect_info['centerY'] - 75
            log(f"📍 Posición calculada: X={click_x:.1f}, Y={click_y:.1f} (75px arriba)")

            movement_type = random.choice(['bezier', 'zigzag', 'circle'])
            if movement_type == 'bezier':
                points = []
                for i in range(3):
                    offset_x = random.randint(-60, 60)
                    offset_y = random.randint(-100, -20)
                    points.append((offset_x, offset_y))
                points.append((0, -75))
                steps = 10
                for step in range(steps):
                    t = step / (steps - 1)
                    idx = int(t * (len(points) - 1))
                    if idx >= len(points) - 1:
                        offset_x, offset_y = points[-1]
                    else:
                        p1 = points[idx]; p2 = points[idx + 1]; local_t = (t * (len(points) - 1)) - idx
                        offset_x = p1[0] + (p2[0] - p1[0]) * local_t
                        offset_y = p1[1] + (p2[1] - p1[1]) * local_t
                    actions = ActionChains(driver)
                    actions.move_to_element_with_offset(search_btn, int(offset_x), int(offset_y))
                    actions.pause(random.uniform(0.05, 0.12))
                    actions.perform()
            elif movement_type == 'zigzag':
                steps = 6
                for i in range(1, steps + 1):
                    progress = i / steps
                    lateral = random.randint(-40, 40) if i < steps else 0
                    vertical = int(-75 * progress)
                    actions = ActionChains(driver)
                    actions.move_to_element_with_offset(search_btn, lateral, vertical)
                    actions.pause(random.uniform(0.08, 0.18))
                    actions.perform()
            else:
                actions = ActionChains(driver)
                actions.move_to_element_with_offset(search_btn, 0, -75)
                actions.perform()
                wait_random(0.2, 0.4)
                import math
                radius = 25
                for i in range(6):
                    angle = (2 * math.pi * i) / 6
                    offset_x = int(radius * math.cos(angle))
                    offset_y = -75 + int(radius * math.sin(angle))
                    actions = ActionChains(driver)
                    actions.move_to_element_with_offset(search_btn, offset_x, offset_y)
                    actions.pause(random.uniform(0.06, 0.12))
                    actions.perform()
                actions = ActionChains(driver)
                actions.move_to_element_with_offset(search_btn, 0, -75)
                actions.perform()

            # Marcador visual
            driver.execute_script("""
                var marker = document.createElement('div');
                marker.id = 'click-marker-test';
                marker.style.position = 'fixed';
                marker.style.left = (arguments[0] - 15) + 'px';
                marker.style.top = (arguments[1] - 15) + 'px';
                marker.style.width = '30px';
                marker.style.height = '30px';
                marker.style.borderRadius = '50%';
                marker.style.backgroundColor = 'rgba(255, 0, 0, 0.6)';
                marker.style.border = '3px solid red';
                marker.style.zIndex = '999999';
                marker.style.pointerEvents = 'none';
                marker.style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.8)';
                document.body.appendChild(marker);
            """, click_x, click_y)
            wait_random(0.8, 1.2)
            save_screenshot(driver, f"04_POSICION_clic2_{slug(apellidos_nombres)}")
            wait_random(0.5, 1.0)

            # Ejecutar clic #2
            actions = ActionChains(driver)
            actions.pause(random.uniform(0.15, 0.35))
            actions.click()
            actions.pause(random.uniform(0.08, 0.18))
            actions.perform()
            log("✅ Clic #2 ejecutado (checkbox reCAPTCHA activado)")

            # remover marcador
            driver.execute_script("var m=document.getElementById('click-marker-test'); if(m) m.remove();")

        except Exception as e:
            log(f"⚠️ Error durante clic en checkbox reCAPTCHA: {e}")
            log("🔄 Intentando clic directo sobre checkbox (offset -75)")
            try:
                actions = ActionChains(driver)
                actions.move_to_element_with_offset(search_btn, 0, -75)
                actions.pause(random.uniform(0.5, 1.0))
                actions.click()
                actions.perform()
                log("✅ Clic #2 exitoso en checkbox (método directo)")
            except Exception as e2:
                log(f"❌ Clic #2 en checkbox también falló: {e2}")
                traceback.print_exc()
                return None

        # ============================
        # 🎯 DETECCIÓN INTELIGENTE: ¿Apareció ventana de imágenes?
        # ============================
        log("⏳ Esperando para detectar si aparece ventana modal de imágenes...")
        wait_random(2.0, 3.0)  # Dar tiempo para que aparezca la ventana si va a aparecer
        
        ventana_imagenes_aparecio = detectar_ventana_imagenes_recaptcha(driver)
        
        if ventana_imagenes_aparecio:
            log("🖼️ ¡Ventana de imágenes detectada! Usando CapSolver para resolver...")
            save_screenshot(driver, f"04b_ventana_imagenes_{slug(apellidos_nombres)}")
            
            try:
                # Obtener sitekey y URL actual
                hay_iframe, sitekey_detected, page_url = detectar_recaptcha_iframe(driver)
                sk = sitekey_detected if sitekey_detected else BURNED_SITEKEY
                
                log(f"🛡️ Resolviendo reCAPTCHA: sitekey={sk}")
                task_id = crear_tarea_capsolver(site_url=page_url, site_key=sk)
                token = obtener_resultado_capsolver(task_id, max_wait_s=180)
                inyectar_token_en_pagina(driver, token)
                
                log("✅ Token inyectado correctamente")
                wait_random(1.5, 2.5)
                save_screenshot(driver, f"04c_despues_resolver_{slug(apellidos_nombres)}")
                
            except Exception as e:
                log(f"❌ Error resolviendo reCAPTCHA con CapSolver: {e}")
                save_screenshot(driver, f"error_recaptcha_{slug(apellidos_nombres)}")
                traceback.print_exc()
        else:
            log("✅ No apareció ventana de imágenes - el checkbox se resolvió automáticamente")
            save_screenshot(driver, f"04b_sin_ventana_imagenes_{slug(apellidos_nombres)}")

        # Espera después del proceso del checkbox y posible resolución de imágenes
        wait_random(1.5, 2.5)
        save_screenshot(driver, f"05_despues_clic2_y_captcha_{slug(apellidos_nombres)}")

        # ===== CLIC #3: otra vez en el botón BUSCAR (flujo normal) =====
        log("🖱️ CLIC #3: Nuevamente en botón BUSCAR")
        wait_random(1.0, 1.8)
        try:
            search_btn = find_search_button(driver)
            if search_btn:
                if selenium_click_element(driver, search_btn, use_human_movement=True):
                    log("✅ Clic #3 ejecutado")
                else:
                    log("⚠️ Clic #3 falló")
            else:
                log("⚠️ Botón BUSCAR no encontrado para clic #3")
        except Exception as e:
            log(f"⚠️ Error en clic #3: {e}")

        wait_random(2.0, 3.5)
        save_screenshot(driver, f"06_despues_clic3_{slug(apellidos_nombres)}")

        # Analizar resultados
        log("=" * 60)
        log("🔍 ANALIZANDO RESPUESTA DEL SISTEMA...")
        log("=" * 60)
        wait_random(2.0, 4.0)

        has_no_results_modal = detect_no_results_modal(driver)
        has_results = detect_results_loaded(driver)

        resultado = {
            "success": True,
            "nombre_buscado": apellidos_nombres,
            "screenshots": []
        }

        if has_no_results_modal:
            log("📋 ESCENARIO: SIN RESULTADOS")
            s = save_screenshot(driver, f"funcion_judicial_{slug(apellidos_nombres)}_SIN_RESULTADOS")
            resultado.update({"scenario": "no_results", "screenshot_path": s, "mensaje": "No se encontraron procesos judiciales"})
            resultado["screenshots"].append(s)
        elif has_results:
            log("📊 ESCENARIO: CON RESULTADOS")
            s = save_screenshot(driver, f"funcion_judicial_{slug(apellidos_nombres)}_RESULTADOS")
            resultado.update({"scenario": "results_found", "screenshot_path": s, "mensaje": "Se encontraron procesos judiciales"})
            resultado["screenshots"].append(s)
        else:
            log("⚠️ ESCENARIO: INDETERMINADO")
            s = save_screenshot(driver, f"funcion_judicial_{slug(apellidos_nombres)}_INDETERMINADO")
            resultado.update({"scenario": "indeterminate", "screenshot_path": s, "mensaje": "No se pudo determinar el estado de los resultados"})
            resultado["screenshots"].append(s)

        # screenshot final
        s_final = save_screenshot(driver, f"08_FINAL_{slug(apellidos_nombres)}")
        resultado["screenshots"].append(s_final)

        log("=" * 60)
        log("✅ CONSULTA COMPLETADA")
        log(f"📋 Escenario: {resultado['scenario']}")
        log(f"💬 Mensaje: {resultado['mensaje']}")
        log(f"📸 Screenshots capturados: {len(resultado['screenshots'])}")
        log("=" * 60)

        wait_random(2.0, 3.0)
        return resultado

    except Exception as e:
        log(f"❌ ERROR EN PRUEBA: {e}")
        traceback.print_exc()
        if driver:
            save_screenshot(driver, f"error_{slug(apellidos_nombres)}")
        return None
    finally:
        if driver:
            log("🔚 Cerrando driver...")
            try:
                driver.quit()
            except:
                pass

# ============= MAIN =============
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Función Judicial con CapSolver INTELIGENTE")
    parser.add_argument("--nombre", type=str, default=NOMBRE_PRUEBA, help=f"Nombre completo a buscar (default: {NOMBRE_PRUEBA})")
    parser.add_argument("--no-headless", action="store_true", help="Ejecutar con GUI visible (para debugging)")
    args = parser.parse_args()

    headless = not args.no_headless
    resultado = test_funcion_judicial_with_capsolver(apellidos_nombres=args.nombre, headless=headless)

    if resultado:
        print("\n" + "=" * 60)
        print("✅ RESULTADO EXITOSO:")
        print(f"   Nombre buscado: {resultado['nombre_buscado']}")
        print(f"   Escenario: {resultado['scenario']}")
        print(f"   Mensaje: {resultado['mensaje']}")
        print(f"   Screenshots capturados: {len(resultado['screenshots'])}")
        print("\n   📸 Screenshots:")
        for i, screenshot in enumerate(resultado['screenshots'], 1):
            print(f"      {i}. {screenshot}")
        print("=" * 60)
    else:
        print("\n❌ PRUEBA FALLÓ - Ver logs arriba")


        # site key del Sitio:   6LfjVAcUAAAAANT1V80aWo