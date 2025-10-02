# test_funcion_judicial_headless.py
"""
Script de prueba independiente para Función Judicial
- Modo headless puro con Selenium
- Sin PyAutoGUI
- Con anti-detección mejorada (evita captchas)
- Solo hasta screenshot después de escribir nombres
"""

import time
import random
import os
from datetime import datetime
from pathlib import Path

# Opción 1: Selenium normal con anti-detección manual
USE_UNDETECTED = True  # Cambiar a False para usar Selenium normal

if USE_UNDETECTED:
    try:
        import undetected_chromedriver as uc
        print("✅ Usando undetected-chromedriver (anti-detección)")
    except ImportError:
        print("⚠️ undetected-chromedriver no instalado")
        print("   Instalar con: pip install undetected-chromedriver")
        USE_UNDETECTED = False

if not USE_UNDETECTED:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    print("ℹ️ Usando Selenium normal con anti-detección manual")

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ============= CONFIGURACIÓN =============
FUNCION_JUDICIAL_URL = "https://procesosjudiciales.funcionjudicial.gob.ec/busqueda-filtros"

# NOMBRES DE PRUEBA QUEMADOS
NOMBRE_PRUEBA = "MARCOS GOMEZ DANIEL CARLOS"

# Directorios
SCREENSHOTS_DIR = Path("screenshots_test")
SCREENSHOTS_DIR.mkdir(exist_ok=True)


# ============= UTILIDADES =============
def log(mensaje):
    """Log simple con timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {mensaje}")


def wait_random(min_sec=0.5, max_sec=2.0):
    """Espera con variación humana"""
    time.sleep(random.uniform(min_sec, max_sec))


def slug(text):
    """Genera slug para nombres de archivo"""
    import re
    return re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '_').lower()


# ============= CREAR DRIVER =============
def create_headless_driver():
    """
    Crea driver de Chrome en modo headless
    Compatible con Linux
    Con anti-detección mejorada
    """
    log("🚀 Creando driver en modo headless con anti-detección...")
    
    if USE_UNDETECTED:
        # ========== UNDETECTED-CHROMEDRIVER (Recomendado) ==========
        log("🥷 Usando undetected-chromedriver (evita detección automáticamente)")
        
        options = uc.ChromeOptions()
        
        # Headless (undetected-chromedriver maneja esto especialmente)
        options.add_argument('--headless=new')
        
        # Configuración para Linux
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Crear driver con undetected
        driver = uc.Chrome(options=options, version_main=None)
        
        log("✅ Driver undetected creado exitosamente")
        
    else:
        # ========== SELENIUM NORMAL CON ANTI-DETECCIÓN MANUAL ==========
        log("🛡️ Usando Selenium normal con anti-detección manual")
        
        options = Options()
        
        # Configuración headless
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # User agent realista
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Deshabilitar automatización detectada
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Deshabilitar blink features
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = webdriver.Chrome(options=options)
        
        # ===== ANTI-DETECCIÓN ADICIONAL =====
        
        # 1. Ocultar navigator.webdriver
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        # 2. Sobrescribir permisos
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' })
                    })
                })
            '''
        })
        
        # 3. Agregar plugins falsos
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                })
            '''
        })
        
        # 4. Sobrescribir languages
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['es-ES', 'es', 'en-US', 'en']
                })
            '''
        })
        
        # 5. Chrome runtime
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                window.chrome = {
                    runtime: {}
                }
            '''
        })
        
        log("✅ Driver creado con anti-detección manual aplicada")
    
    return driver


# ============= MOVIMIENTOS HUMANOS (REEMPLAZO DE PYAUTOGUI) =============

def random_scroll_smooth(driver, direction='down', distance=None):
    """
    Scroll aleatorio suave que simula lectura humana
    """
    if distance is None:
        distance = random.randint(100, 400)
    
    if direction == 'down':
        distance = abs(distance)
    else:
        distance = -abs(distance)
    
    # Scroll en pasos pequeños con pausas
    steps = random.randint(8, 15)
    step_size = distance / steps
    
    for _ in range(steps):
        driver.execute_script(f"window.scrollBy(0, {step_size});")
        time.sleep(random.uniform(0.02, 0.08))
    
    # Pequeña corrección al final (simula ajuste humano)
    correction = random.randint(-20, 20)
    driver.execute_script(f"window.scrollBy(0, {correction});")
    time.sleep(random.uniform(0.1, 0.2))


def move_mouse_in_circle(driver, element, radius=50):
    """
    Mueve el mouse en un pequeño círculo alrededor del elemento
    Simula búsqueda visual del objetivo
    """
    import math
    
    log("🔄 Movimiento circular del cursor (simulando búsqueda)...")
    
    actions = ActionChains(driver)
    
    # Mover al elemento primero
    actions.move_to_element(element).perform()
    
    # Crear círculo con 8 puntos
    points = 8
    for i in range(points):
        angle = (2 * math.pi * i) / points
        offset_x = int(radius * math.cos(angle))
        offset_y = int(radius * math.sin(angle))
        
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(element, offset_x, offset_y)
        actions.pause(random.uniform(0.05, 0.12))
        actions.perform()
    
    # Volver al centro
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.pause(random.uniform(0.1, 0.2))
    actions.perform()
    
    log("✅ Movimiento circular completado")


def move_mouse_zigzag(driver, element, steps=5):
    """
    Mueve el mouse en zigzag hacia el elemento
    Simula movimiento natural humano (no en línea recta)
    """
    log("↔️ Movimiento en zigzag del cursor...")
    
    actions = ActionChains(driver)
    
    # Puntos intermedios con desviación lateral
    for i in range(1, steps + 1):
        progress = i / steps
        
        # Desviación lateral aleatoria (zigzag)
        lateral_offset = random.randint(-30, 30) if i < steps else 0
        vertical_offset = int(-50 * progress)  # Avanzar hacia el elemento
        
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(element, lateral_offset, vertical_offset)
        actions.pause(random.uniform(0.05, 0.15))
        actions.perform()
    
    # Movimiento final al centro exacto
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.pause(random.uniform(0.1, 0.2))
    actions.perform()
    
    log("✅ Movimiento en zigzag completado")


def move_mouse_bezier_curve(driver, element, control_points=3):
    """
    Mueve el mouse siguiendo una curva Bézier
    Simula el movimiento natural del cursor humano
    """
    import math
    
    log("📐 Movimiento en curva Bézier (simulando humano)...")
    
    # Crear curva con puntos de control aleatorios
    points = []
    for i in range(control_points):
        # Generar puntos de control con desviación
        offset_x = random.randint(-80, 80)
        offset_y = random.randint(-80, 80)
        points.append((offset_x, offset_y))
    
    # Agregar punto final (centro del elemento)
    points.append((0, 0))
    
    # Interpolar puntos a lo largo de la curva
    steps = 12
    for step in range(steps):
        t = step / (steps - 1)
        
        # Interpolación simple (Bézier cuadrática)
        if len(points) >= 3:
            # Punto en la curva
            idx = int(t * (len(points) - 1))
            if idx >= len(points) - 1:
                offset_x, offset_y = points[-1]
            else:
                p1 = points[idx]
                p2 = points[idx + 1]
                local_t = (t * (len(points) - 1)) - idx
                offset_x = p1[0] + (p2[0] - p1[0]) * local_t
                offset_y = p1[1] + (p2[1] - p1[1]) * local_t
        else:
            offset_x, offset_y = 0, 0
        
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(element, int(offset_x), int(offset_y))
        actions.pause(random.uniform(0.04, 0.1))
        actions.perform()
    
    log("✅ Movimiento en curva completado")


def human_like_scroll_and_read(driver):
    """
    Simula lectura humana de la página con scroll
    """
    log("👁️ Simulando lectura de página con scroll...")
    
    # Scroll down un poco
    random_scroll_smooth(driver, 'down', random.randint(150, 300))
    wait_random(0.5, 1.2)
    
    # Scroll up un poco (como revisando)
    random_scroll_smooth(driver, 'up', random.randint(50, 150))
    wait_random(0.3, 0.8)
    
    # Scroll down de nuevo
    random_scroll_smooth(driver, 'down', random.randint(100, 250))
    wait_random(0.4, 0.9)
    
    # Volver al top
    driver.execute_script("window.scrollTo(0, 0);")
    wait_random(0.3, 0.6)
    
    log("✅ Simulación de lectura completada")


# ============= DETECCIÓN DE RESULTADOS =============

def detect_no_results_modal(driver, timeout=5):
    """
    Detecta si apareció el modal de "sin resultados"
    Busca textos como: "No se encontraron resultados", "Sin datos", etc.
    """
    log("🔍 Verificando si apareció modal de 'sin resultados'...")
    
    try:
        # Selectores comunes para modales de "sin resultados"
        no_results_selectors = [
            "//div[contains(text(), 'La consulta no devolvió resultados')]",
            "//div[contains(text(), 'La consulta no devolvió resultados. Cerrar')]",
            "//span[contains(text(), 'La consulta no devolvió resultadosn')]",
            "//p[contains(text(), 'La consulta no devolvió resultados')]",
            "//*[contains(@class, 'La consulta no devolvió resultados')]",
            "//*[contains(@class, 'La consulta no devolvió resultados. Cerrar')]",
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
        
        # Verificar por JavaScript también
        try:
            result = driver.execute_script("""
                const text = document.body.innerText.toLowerCase();
                return text.includes('La consulta no devolvió resultados. Cerrar') || 
                       text.includes('La consulta no devolvió resultados.') ||
                       text.includes('La consulta no devolvió resultados');
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
    """
    Detecta si se cargaron resultados (tabla, lista, cards, etc.)
    """
    log("🔍 Verificando si hay resultados cargados...")
    
    try:
        # Esperar un momento para que carguen los resultados
        wait_random(2.0, 3.0)
        
        # Selectores comunes para tablas/listas de resultados
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
        
        # Verificar contenedor de resultados específico
        try:
            results_container = driver.find_element(By.CSS_SELECTOR, 
                "body > app-root > app-expel-listado-juicios > expel-sidenav > mat-sidenav-container > mat-sidenav-content > section"
            )
            if results_container.is_displayed():
                # Verificar que tenga contenido significativo
                content_height = driver.execute_script(
                    "return arguments[0].scrollHeight;", 
                    results_container
                )
                if content_height > 200:  # Altura mínima para considerar que hay resultados
                    log(f"✅ Contenedor de resultados detectado (altura: {content_height}px)")
                    return True
        except:
            pass
        
        log("ℹ️ No se detectaron resultados cargados")
        return False
        
    except Exception as e:
        log(f"⚠️ Error detectando resultados: {e}")
        return False


def capture_no_results_screenshot(driver, base_name):
    """
    Captura screenshot del modal de sin resultados
    """
    log("📸 Capturando screenshot del modal 'sin resultados'...")
    
    filepath = SCREENSHOTS_DIR / f"{base_name}_SIN_RESULTADOS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    try:
        driver.save_screenshot(str(filepath))
        log(f"✅ Screenshot sin resultados guardado: {filepath}")
        return str(filepath)
    except Exception as e:
        log(f"❌ Error capturando screenshot: {e}")
        return None


def capture_results_page(driver, base_name, page_number=1):
    """
    Captura screenshot de una página de resultados
    """
    log(f"📸 Capturando screenshot de página {page_number} de resultados...")
    
    filepath = SCREENSHOTS_DIR / f"{base_name}_RESULTADOS_page{page_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    try:
        # Scroll suave para asegurar que todo esté visible
        random_scroll_smooth(driver, 'down', 100)
        wait_random(0.5, 0.8)
        random_scroll_smooth(driver, 'up', 50)
        wait_random(0.3, 0.5)
        
        driver.save_screenshot(str(filepath))
        log(f"✅ Screenshot página {page_number} guardado: {filepath}")
        return str(filepath)
    except Exception as e:
        log(f"❌ Error capturando screenshot: {e}")
        return None


# ============= FUNCIONES DE SELENIUM CON MOVIMIENTOS HUMANOS =============
def human_type_selenium(driver, element, text, base_delay=0.15):
    """
    Escribe texto caracter por caracter simulando escritura humana
    Con movimientos de scroll aleatorios durante la escritura
    """
    log(f"✏️ Escribiendo: {text}")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
    wait_random(0.5, 1.0)
    
    # Limpiar campo con delay
    element.clear()
    wait_random(0.5, 1.0)
    
    # Click en el campo (con movimiento previo)
    try:
        actions = ActionChains(driver)
        # Movimiento no directo al campo
        actions.move_to_element_with_offset(element, random.randint(-10, 10), random.randint(-5, 5))
        actions.pause(random.uniform(0.2, 0.4))
        actions.move_to_element(element)
        actions.pause(random.uniform(0.1, 0.3))
        actions.click()
        actions.perform()
    except:
        element.click()
    
    wait_random(0.3, 0.6)
    
    # Escribir caracter por caracter
    for i, char in enumerate(text):
        element.send_keys(char)
        
        # Delay variable entre caracteres (más lento y natural)
        delay = max(0.08, random.gauss(base_delay, base_delay * 0.4))
        time.sleep(delay)
        
        # Pausas más largas en espacios
        if char in ' ':
            time.sleep(random.uniform(0.15, 0.35))
        elif char in ',.;:':
            time.sleep(random.uniform(0.2, 0.4))
        
        # Cada 5-8 caracteres, pausa adicional (simula pensar)
        if i > 0 and i % random.randint(5, 8) == 0:
            time.sleep(random.uniform(0.15, 0.35))
            
            # A veces mover el mouse un poco (como distracción humana)
            if random.random() < 0.3:
                try:
                    actions = ActionChains(driver)
                    actions.move_by_offset(random.randint(-20, 20), random.randint(-20, 20))
                    actions.pause(0.1)
                    actions.perform()
                    # Volver al campo
                    actions = ActionChains(driver)
                    actions.move_to_element(element)
                    actions.perform()
                except:
                    pass
    
    log(f"✅ Texto escrito ({len(text)} caracteres)")


def selenium_click_element(driver, element, use_human_movement=True):
    """
    Click en elemento usando solo Selenium
    Con movimientos humanos realistas (curvas, zigzag, círculos)
    """
    log("🖱️ Preparando click con movimientos humanos...")
    
    try:
        # Scroll al elemento suavemente
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
        wait_random(0.8, 1.5)
        
        # Pequeño scroll adicional aleatorio (como ajustando la vista)
        random_scroll_smooth(driver, random.choice(['up', 'down']), random.randint(20, 80))
        wait_random(0.3, 0.7)
        
        if use_human_movement:
            # Elegir tipo de movimiento aleatorio
            movement_type = random.choice(['zigzag', 'circle', 'bezier', 'direct'])
            
            if movement_type == 'zigzag':
                move_mouse_zigzag(driver, element, steps=random.randint(4, 7))
            elif movement_type == 'circle':
                move_mouse_in_circle(driver, element, radius=random.randint(30, 60))
            elif movement_type == 'bezier':
                move_mouse_bezier_curve(driver, element, control_points=random.randint(2, 4))
            else:
                # Movimiento "directo" pero con pequeñas desviaciones
                actions = ActionChains(driver)
                # Primero cerca pero no exacto
                actions.move_to_element_with_offset(element, random.randint(-15, 15), random.randint(-10, 10))
                actions.pause(random.uniform(0.2, 0.4))
                # Luego al centro
                actions.move_to_element(element)
                actions.pause(random.uniform(0.2, 0.5))
                actions.perform()
        else:
            # Movimiento simple
            actions = ActionChains(driver)
            actions.move_to_element(element)
            actions.pause(random.uniform(0.3, 0.7))
            actions.perform()
        
        # Pausa antes del click (mano sobre el botón)
        wait_random(0.4, 0.9)
        
        # Click con pequeña variación
        actions = ActionChains(driver)
        actions.click()
        actions.pause(random.uniform(0.08, 0.18))  # Simula tiempo de presión del botón
        actions.perform()
        
        log("✅ Click exitoso con movimientos humanos")
        return True
        
    except Exception as e:
        log(f"⚠️ Movimientos humanos fallaron: {e}, intentando JavaScript...")
        
        try:
            wait_random(0.3, 0.6)
            driver.execute_script("arguments[0].click();", element)
            log("✅ Click exitoso (JavaScript fallback)")
            return True
            
        except Exception as e2:
            log(f"❌ JavaScript click también falló: {e2}")
            return False


def save_screenshot(driver, nombre_archivo):
    """Guarda screenshot completo de la página"""
    filepath = SCREENSHOTS_DIR / f"{nombre_archivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    try:
        driver.save_screenshot(str(filepath))
        log(f"📸 Screenshot guardado: {filepath}")
        return str(filepath)
    except Exception as e:
        log(f"❌ Error guardando screenshot: {e}")
        return None


# ============= BÚSQUEDA DE ELEMENTOS =============
def find_name_input(driver, timeout=15):
    """Encuentra el campo de nombres (#mat-input-4)"""
    log("🔍 Buscando campo de nombres...")
    
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "mat-input-4"))
        )
        log("✅ Campo de nombres encontrado: #mat-input-4")
        return element
        
    except TimeoutException:
        log("⚠️ No se encontró por ID, intentando XPath...")
        
        try:
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="mat-input-4"]'))
            )
            log("✅ Campo de nombres encontrado: XPath")
            return element
            
        except TimeoutException:
            log("❌ No se pudo encontrar el campo de nombres")
            return None


def find_search_button(driver, timeout=15):
    """Encuentra el botón de búsqueda"""
    log("🔍 Buscando botón de búsqueda...")
    
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR, 
                "button.boton-buscar.mdc-button.mdc-button--raised.mat-mdc-raised-button.mat-accent"
            ))
        )
        log("✅ Botón de búsqueda encontrado")
        return element
        
    except TimeoutException:
        log("⚠️ No se encontró el botón con CSS, intentando XPath...")
        
        try:
            element = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//button[contains(@class, 'boton-buscar')]"
                ))
            )
            log("✅ Botón de búsqueda encontrado: XPath")
            return element
            
        except TimeoutException:
            log("❌ No se pudo encontrar el botón de búsqueda")
            return None


# ============= PROCESO PRINCIPAL =============
def test_funcion_judicial_headless(apellidos_nombres, headless=True):
    """
    Proceso de prueba:
    1. Navegar a Función Judicial
    2. Escribir nombres y apellidos
    3. Tomar screenshot
    """
    driver = None
    
    try:
        log("=" * 60)
        log(f"🏛️ INICIANDO PRUEBA FUNCIÓN JUDICIAL")
        log(f"📝 Nombre a buscar: {apellidos_nombres}")
        log(f"🎭 Modo headless: {headless}")
        log("=" * 60)
        
        # 1. Crear driver
        if headless:
            driver = create_headless_driver()
        else:
            # Para pruebas con GUI
            options = Options()
            options.add_argument('--window-size=1920,1080')
            driver = webdriver.Chrome(options=options)
        
        # 2. Navegar a la página
        log(f"🌐 Navegando a: {FUNCION_JUDICIAL_URL}")
        driver.get(FUNCION_JUDICIAL_URL)
        
        # Espera inicial más larga (simula carga humana)
        log("⏳ Esperando carga inicial de la página...")
        wait_random(3.0, 5.0)
        
        # Screenshot inicial
        save_screenshot(driver, f"01_pagina_inicial_{slug(apellidos_nombres)}")
        
        # SIMULAR COMPORTAMIENTO HUMANO: Scroll y lectura
        log("📖 Simulando lectura humana de la página...")
        human_like_scroll_and_read(driver)
        
        # 3. Encontrar campo de nombres
        log("🔍 Esperando que el formulario esté listo...")
        wait_random(1.0, 2.0)
        
        name_input = find_name_input(driver)
        if not name_input:
            log("❌ No se encontró el campo de nombres")
            return None
        
        # Movimiento del mouse hacia el campo (simulando búsqueda visual)
        log("👀 Localizando campo de entrada...")
        try:
            # Movimiento en círculo pequeño alrededor del campo
            move_mouse_in_circle(driver, name_input, radius=40)
        except Exception as e:
            log(f"⚠️ Movimiento circular falló: {e}")
        
        wait_random(0.5, 1.0)
        
        # 4. Escribir apellidos y nombres
        log(f"✍️ Escribiendo en el campo: {apellidos_nombres}")
        human_type_selenium(driver, name_input, apellidos_nombres)
        wait_random(1.0, 2.0)
        
        # 5. Screenshot después de escribir
        save_screenshot(driver, f"02_despues_escribir_{slug(apellidos_nombres)}")
        
        # Scroll aleatorio después de escribir (como revisando lo escrito)
        log("👁️ Revisando datos ingresados...")
        random_scroll_smooth(driver, 'down', random.randint(50, 120))
        wait_random(0.5, 1.0)
        random_scroll_smooth(driver, 'up', random.randint(30, 80))
        wait_random(0.8, 1.5)
        
        # 6. Encontrar botón de búsqueda
        search_btn = find_search_button(driver)
        if not search_btn:
            log("❌ No se encontró el botón de búsqueda")
            return None
        
        # 7. SECUENCIA DE CLICS ESPECIAL (solo hasta clic #2)
        log("🔍 Iniciando secuencia de clics especial...")
        screenshots_paths = []
        
        # Movimiento del cursor hacia el botón (búsqueda visual)
        log("👀 Localizando botón de búsqueda...")
        try:
            # Zigzag hacia el botón
            move_mouse_zigzag(driver, search_btn, steps=random.randint(5, 7))
        except Exception as e:
            log(f"⚠️ Movimiento zigzag falló: {e}")
        
        wait_random(0.5, 1.0)
        
        # === CLIC #1: En el botón BUSCAR ===
        log("🖱️ CLIC #1: En botón BUSCAR")
        if not selenium_click_element(driver, search_btn, use_human_movement=True):
            log("❌ Falló clic #1")
            return None
        
        wait_random(1.5, 2.5)
        save_screenshot(driver, f"03_despues_clic1_{slug(apellidos_nombres)}")
        
        # Scroll aleatorio después del primer clic
        log("📖 Scroll aleatorio post-clic #1...")
        random_scroll_smooth(driver, random.choice(['up', 'down']), random.randint(40, 100))
        wait_random(0.5, 1.0)
        
        # === CLIC #2: 75px arriba del botón (ventanita) ===
        log("🖱️ CLIC #2: Preparando posición (75px arriba del botón)")
        
        # Pausa antes del segundo clic (simula análisis)
        wait_random(1.0, 2.0)
        
        try:
            # Calcular posición exacta del clic
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
            
            log(f"📍 Posición calculada: X={click_x:.1f}, Y={click_y:.1f} (75px arriba del botón)")
            
            # MOVIMIENTO HUMANO HACIA LA POSICIÓN DEL CLIC #2
            log("🎯 Movimiento humano hacia posición del clic #2...")
            
            # Elegir tipo de movimiento aleatorio
            movement_type = random.choice(['bezier', 'zigzag', 'circle'])
            
            if movement_type == 'bezier':
                # Curva Bézier hacia arriba del botón
                log("📐 Usando curva Bézier...")
                points = []
                for i in range(3):
                    offset_x = random.randint(-60, 60)
                    offset_y = random.randint(-100, -20)
                    points.append((offset_x, offset_y))
                points.append((0, -75))  # Posición final
                
                steps = 10
                for step in range(steps):
                    t = step / (steps - 1)
                    idx = int(t * (len(points) - 1))
                    if idx >= len(points) - 1:
                        offset_x, offset_y = points[-1]
                    else:
                        p1 = points[idx]
                        p2 = points[idx + 1]
                        local_t = (t * (len(points) - 1)) - idx
                        offset_x = p1[0] + (p2[0] - p1[0]) * local_t
                        offset_y = p1[1] + (p2[1] - p1[1]) * local_t
                    
                    actions = ActionChains(driver)
                    actions.move_to_element_with_offset(search_btn, int(offset_x), int(offset_y))
                    actions.pause(random.uniform(0.05, 0.12))
                    actions.perform()
            
            elif movement_type == 'zigzag':
                # Zigzag hacia arriba
                log("↔️ Usando zigzag vertical...")
                steps = 6
                for i in range(1, steps + 1):
                    progress = i / steps
                    lateral = random.randint(-40, 40) if i < steps else 0
                    vertical = int(-75 * progress)
                    
                    actions = ActionChains(driver)
                    actions.move_to_element_with_offset(search_btn, lateral, vertical)
                    actions.pause(random.uniform(0.08, 0.18))
                    actions.perform()
            
            else:  # circle
                # Círculo pequeño en la posición objetivo
                log("🔄 Usando círculo en posición...")
                # Primero mover cerca
                actions = ActionChains(driver)
                actions.move_to_element_with_offset(search_btn, 0, -75)
                actions.perform()
                wait_random(0.2, 0.4)
                
                # Luego círculo pequeño
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
                
                # Volver al centro de la posición
                actions = ActionChains(driver)
                actions.move_to_element_with_offset(search_btn, 0, -75)
                actions.perform()
            
            log("✅ Cursor movido con movimientos humanos")
            
            # INYECTAR MARCADOR VISUAL
            log("🎯 Inyectando marcador visual en la posición del clic...")
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
                
                var cross = document.createElement('div');
                cross.style.position = 'absolute';
                cross.style.left = '50%';
                cross.style.top = '50%';
                cross.style.transform = 'translate(-50%, -50%)';
                cross.style.width = '2px';
                cross.style.height = '20px';
                cross.style.backgroundColor = 'yellow';
                marker.appendChild(cross);
                
                var cross2 = document.createElement('div');
                cross2.style.position = 'absolute';
                cross2.style.left = '50%';
                cross2.style.top = '50%';
                cross2.style.transform = 'translate(-50%, -50%)';
                cross2.style.width = '20px';
                cross2.style.height = '2px';
                cross2.style.backgroundColor = 'yellow';
                marker.appendChild(cross2);
            """, click_x, click_y)
            
            log("✅ Marcador visual inyectado")
            
            # SCREENSHOT CON MARCADOR
            wait_random(0.8, 1.2)
            screenshot_antes_clic2 = save_screenshot(
                driver, 
                f"04_POSICION_clic2_{slug(apellidos_nombres)}"
            )
            log(f"📸 Screenshot ANTES del clic #2 (con marcador): {screenshot_antes_clic2}")
            log("🔍 REVISA ESTE SCREENSHOT para ver el marcador rojo")
            
            # HACER CLIC #2
            wait_random(0.5, 1.0)
            log("🖱️ Ejecutando clic #2 ahora...")
            actions = ActionChains(driver)
            actions.pause(random.uniform(0.15, 0.35))  # Pausa antes del clic
            actions.click()
            actions.pause(random.uniform(0.08, 0.18))  # Simula presión del botón
            actions.perform()
            log("✅ Clic #2 ejecutado")
            
            # Remover marcador
            driver.execute_script("""
                var marker = document.getElementById('click-marker-test');
                if (marker) marker.remove();
            """)
            
        except Exception as e:
            log(f"⚠️ Movimientos humanos fallaron en clic #2: {e}")
            log("🔄 Intentando método directo...")
            
            try:
                actions = ActionChains(driver)
                actions.move_to_element_with_offset(search_btn, 0, -75)
                actions.pause(random.uniform(0.5, 1.0))
                actions.click()
                actions.perform()
                log("✅ Clic #2 exitoso (método directo)")
            except Exception as e2:
                log(f"❌ Clic #2 también falló: {e2}")
                return None
        
        wait_random(2.0, 3.0)
        
        # 8. SCREENSHOT DESPUÉS DEL CLIC #2
        save_screenshot(driver, f"05_despues_clic2_{slug(apellidos_nombres)}")
        
        # Scroll aleatorio después del clic #2
        log("📖 Scroll aleatorio post-clic #2...")
        random_scroll_smooth(driver, random.choice(['up', 'down']), random.randint(30, 90))
        wait_random(0.6, 1.2)
        
        # === CLIC #3: Nuevamente en el botón BUSCAR ===
        log("🖱️ CLIC #3: Nuevamente en botón BUSCAR")
        
        # Pausa antes del tercer clic
        wait_random(1.0, 1.8)
        
        # Verificar que el botón sigue disponible
        try:
            search_btn = find_search_button(driver)
            if not search_btn:
                log("⚠️ Botón BUSCAR no encontrado para clic #3, continuando...")
            else:
                # Movimiento humano hacia el botón (búsqueda visual nuevamente)
                log("👀 Localizando botón para clic #3...")
                try:
                    # Elegir movimiento aleatorio diferente
                    movement_type = random.choice(['bezier', 'circle', 'zigzag'])
                    
                    if movement_type == 'bezier':
                        move_mouse_bezier_curve(driver, search_btn, control_points=random.randint(2, 3))
                    elif movement_type == 'circle':
                        move_mouse_in_circle(driver, search_btn, radius=random.randint(35, 55))
                    else:
                        move_mouse_zigzag(driver, search_btn, steps=random.randint(4, 6))
                        
                except Exception as e:
                    log(f"⚠️ Movimiento previo al clic #3 falló: {e}")
                
                wait_random(0.5, 1.0)
                
                # Ejecutar clic #3 con movimientos humanos
                if selenium_click_element(driver, search_btn, use_human_movement=True):
                    log("✅ Clic #3 ejecutado exitosamente")
                else:
                    log("⚠️ Clic #3 falló, continuando...")
        
        except Exception as e:
            log(f"⚠️ Error en clic #3: {e}, continuando...")
        
        wait_random(2.0, 3.5)
        
        # 9. SCREENSHOT FINAL DESPUÉS DEL CLIC #3
        save_screenshot(driver, f"06_despues_clic3_{slug(apellidos_nombres)}")
        
        # 10. DETECCIÓN DE RESULTADOS VS SIN RESULTADOS
        log("=" * 60)
        log("🔍 ANALIZANDO RESPUESTA DEL SISTEMA...")
        log("=" * 60)
        
        # Esperar que el sistema responda
        wait_random(2.0, 4.0)
        
        # Verificar escenarios
        has_no_results_modal = detect_no_results_modal(driver)
        has_results = detect_results_loaded(driver)
        
        resultado = {
            "success": True,
            "nombre_buscado": apellidos_nombres,
            "screenshots": []
        }
        
        if has_no_results_modal:
            # ESCENARIO 1: Sin resultados detectado
            log("📋 ESCENARIO: SIN RESULTADOS")
            log("ℹ️ El sistema indica que no hay procesos judiciales")
            
            # Capturar modal de sin resultados
            screenshot_sin_resultados = capture_no_results_screenshot(
                driver,
                f"funcion_judicial_{slug(apellidos_nombres)}"
            )
            
            resultado["scenario"] = "no_results"
            resultado["screenshot_path"] = screenshot_sin_resultados
            resultado["mensaje"] = "No se encontraron procesos judiciales"
            resultado["screenshots"].append(screenshot_sin_resultados)
            
            log("✅ Proceso completado - Sin resultados")
            
        elif has_results:
            # ESCENARIO 2: Resultados encontrados
            log("📊 ESCENARIO: CON RESULTADOS")
            log("✅ Se encontraron procesos judiciales")
            
            # Capturar primera página de resultados
            screenshot_resultados = capture_results_page(
                driver,
                f"funcion_judicial_{slug(apellidos_nombres)}",
                page_number=1
            )
            
            resultado["scenario"] = "results_found"
            resultado["screenshot_path"] = screenshot_resultados
            resultado["mensaje"] = "Se encontraron procesos judiciales"
            resultado["screenshots"].append(screenshot_resultados)
            
            log("✅ Proceso completado - Con resultados")
            
            # TODO: En futuras versiones, implementar paginación para capturar más páginas
            log("📝 NOTA: Paginación pendiente de implementar")
            
        else:
            # ESCENARIO 3: Estado indeterminado (puede ser carga lenta o error)
            log("⚠️ ESCENARIO: INDETERMINADO")
            log("⚠️ No se pudo determinar si hay resultados o no")
            
            # Capturar estado actual
            screenshot_indeterminado = save_screenshot(
                driver,
                f"07_estado_indeterminado_{slug(apellidos_nombres)}"
            )
            
            resultado["scenario"] = "indeterminate"
            resultado["screenshot_path"] = screenshot_indeterminado
            resultado["mensaje"] = "No se pudo determinar el estado de los resultados"
            resultado["screenshots"].append(screenshot_indeterminado)
            
            log("⚠️ Proceso completado - Estado indeterminado (revisar manualmente)")
        
        # Screenshot final del estado completo
        screenshot_final = save_screenshot(
            driver,
            f"08_FINAL_{slug(apellidos_nombres)}"
        )
        resultado["screenshots"].append(screenshot_final)
        
        log("=" * 60)
        log("✅ CONSULTA FUNCIÓN JUDICIAL COMPLETADA")
        log(f"📋 Escenario: {resultado['scenario']}")
        log(f"💬 Mensaje: {resultado['mensaje']}")
        log(f"📸 Screenshots capturados: {len(resultado['screenshots'])}")
        log("=" * 60)
        
        # Esperar un poco más antes de cerrar
        wait_random(2.0, 3.0)
        
        return resultado
        
    except Exception as e:
        log(f"❌ ERROR EN PRUEBA: {e}")
        import traceback
        traceback.print_exc()
        
        if driver:
            save_screenshot(driver, f"error_{slug(apellidos_nombres)}")
        
        return None
        
    finally:
        if driver:
            log("🔚 Cerrando driver...")
            try:
                driver.quit()
            except Exception:
                pass


# ============= MAIN =============
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Función Judicial Headless")
    parser.add_argument(
        "--nombre",
        type=str,
        default=NOMBRE_PRUEBA,
        help=f"Nombre completo a buscar (default: {NOMBRE_PRUEBA})"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Ejecutar con GUI visible (para debugging)"
    )
    
    args = parser.parse_args()
    
    # Ejecutar prueba
    resultado = test_funcion_judicial_headless(
        apellidos_nombres=args.nombre,
        headless=not args.no_headless
    )
    
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