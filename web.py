# web.py
# Scraper SRI (Consulta RUC) con comportamiento humano y flujo HITL.
# NO automatiza la resolución del CAPTCHA: tú lo resuelves manualmente y el script continúa.
# La detección de "RUC ya en caché" está COMENTADA (no omite RUCs por caché).

import os
import re
import csv
import sys
import time
import json
import math
import random
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# ===================== Dependencias =====================
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException,
    ElementNotInteractableException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service


import requests
import base64
from PIL import Image
from io import BytesIO


# ===================== Configuración Capsolver =====================
CAPSOLVER_API_KEY = "CAP-6A1AB119B5D19E99F0A7F91E2A78F264CB84F5EEB75AA61FCBA4B9A6121504D2"
CAPSOLVER_URL = "https://api-stable.capsolver.com/createTask"
CAPSOLVER_RESULT_URL = "https://api-stable.capsolver.com/getTaskResult"

# Mapeo de preguntas de reCAPTCHA
RECAPTCHA_QUESTIONS = {
    "/m/0pg52": "taxis",
    "/m/01bjv": "autobús", 
    "/m/02yvhj": "autobús escolar",
    "/m/04_sv": "motocicletas",
    "/m/013xlm": "tractores",
    "/m/01jk_4": "chimeneas",
    "/m/014xcs": "cruces peatonales",
    "/m/015qff": "semáforos",
    "/m/0199g": "bicicletas",
    "/m/015qbp": "parquímetros",
    "/m/0k4j": "coches",
    "/m/015kr": "puentes",
    "/m/019jd": "barcos",
    "/m/0cdl1": "palmeras",
    "/m/09d_r": "montañas o colinas",
    "/m/01pns0": "hidrante",
    "/m/01lynh": "escaleras"
}


# Movimiento de cursor real:
# pip install pyautogui
import pyautogui


# ===================== Configuración =====================
load_dotenv()  # lee .env si existe

SRI_URL = os.getenv(
    "SRI_BASE_URL",
    "https://srienlinea.sri.gob.ec/sri-en-linea/SriRucWeb/ConsultaRuc/Consultas/consultaRuc"
)

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "sri_ruc_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Caché: se guarda, pero NO se usa para saltarse consultas (detección comentada)
CACHE_HOURS = int(os.getenv("CACHE_HOURS", "24"))

# Delays “humanos”
TYPE_BASE_DELAY = float(os.getenv("TYPE_BASE_DELAY", "0.7"))     # ~0.7 s por tecla
TYPE_JITTER = float(os.getenv("TYPE_JITTER", "0.15"))            # variación gaussiana
TYPE_PUNCT_PAUSE = float(os.getenv("TYPE_PUNCT_PAUSE", "0.6"))   # pausa extra tras signos

# Timeouts
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))
RESULTS_TIMEOUT = int(os.getenv("RESULTS_TIMEOUT", "60"))
RECAPTCHA_TIMEOUT = int(os.getenv("RECAPTCHA_TIMEOUT", "180"))

# Reintentos por RUC
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

# Movimiento de mouse curvo
MOUSE_MIN_TIME = float(os.getenv("MOUSE_MIN_TIME", "0.7"))
MOUSE_MAX_TIME = float(os.getenv("MOUSE_MAX_TIME", "1.2"))
MOUSE_STEPS = int(os.getenv("MOUSE_STEPS", "28"))
MOUSE_JITTER = int(os.getenv("MOUSE_JITTER", "2"))

# Leer RUCs desde CSV (opcional)
RUC_CSV = os.getenv("RUC_CSV", "rucs.csv")  # si existe, se usa este archivo


# ===================== Utilidades =====================
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def human_sleep(a=0.8, b=1.9):
    time.sleep(random.uniform(a, b))


def save_screenshot(driver, name: str):
    path = os.path.join(OUTPUT_DIR, name)
    driver.save_screenshot(path)
    log(f"📸 Screenshot guardado: {path}")


def csv_write_rows(path: str, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow(r)


def load_cache() -> Dict[str, Dict]:
    cache_path = os.path.join(OUTPUT_DIR, "cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: Dict[str, Dict]):
    cache_path = os.path.join(OUTPUT_DIR, "cache.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def cache_hit(cache: Dict[str, Dict], ruc: str) -> Optional[Dict]:
    item = cache.get(ruc)
    if not item:
        return None
    try:
        ts = datetime.fromisoformat(item["timestamp"])
        if datetime.now() - ts < timedelta(hours=CACHE_HOURS):
            return item["data"]
    except Exception:
        return None
    return None


# ===================== Tipeo humano =====================
def human_type(element, text, base_delay=TYPE_BASE_DELAY, jitter=TYPE_JITTER, punctuation_pause=TYPE_PUNCT_PAUSE):
    """
    Escribe carácter por carácter con pausas variables.
    """
    try:
        element.clear()
    except Exception:
        pass
    for ch in text:
        element.send_keys(ch)
        delay = max(0.03, random.gauss(mu=base_delay, sigma=base_delay * jitter))
        time.sleep(delay)
        if ch in ",.;:?!":
            time.sleep(punctuation_pause + random.uniform(0.0, 0.3))


# ===================== Trayectorias curvas del mouse =====================
def _ease_in_out_quad(t: float) -> float:
    return 2*t*t if t < 0.5 else -1 + (4 - 2*t)*t


def _bezier_cubic(p0, p1, p2, p3, t):
    x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
    y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def _random_ctrl_points(p0, p3, curvature_px=120):
    x0, y0 = p0; x3, y3 = p3
    dx, dy = x3 - x0, y3 - y0
    nx, ny = -dy, dx
    length = math.hypot(nx, ny) or 1.0
    nx, ny = nx/length, ny/length
    mag1 = random.uniform(curvature_px*0.5, curvature_px*1.2)
    mag2 = random.uniform(curvature_px*0.5, curvature_px*1.2)
    p1 = (x0 + dx*0.33 + nx*mag1, y0 + dy*0.33 + ny*mag1)
    p2 = (x0 + dx*0.66 - nx*mag2, y0 + dy*0.66 - ny*mag2)
    return p1, p2


def get_element_screen_center(driver, element):
    """
    Devuelve (screenX, screenY) del centro del elemento en coordenadas de pantalla.
    Requiere ventana visible (no headless).
    """
    js = """
    const rect = arguments[0].getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const sx = window.screenX || window.screenLeft || 0;
    const sy = window.screenY || window.screenTop || 0;
    const chromeTop = (window.outerHeight - window.innerHeight);
    const chromeLeft = (window.outerWidth - window.innerWidth);
    const cx = rect.left + rect.width/2;
    const cy = rect.top + rect.height/2;
    const screenX = (sx + cx + (chromeLeft/2));
    const screenY = (sy + cy + chromeTop);
    return [screenX * dpr, screenY * dpr, dpr];
    """
    x, y, dpr = driver.execute_script(js, element)
    return (x, y)


def smooth_scroll_into_view(driver, element, steps=12, step_ms=0.02):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    for _ in range(steps):
        delta = random.randint(-2, 2)
        driver.execute_script(f"window.scrollBy(0, {delta});")
        time.sleep(step_ms + random.uniform(0, 0.01))


def move_mouse_curve_and_click(target_xy, total_duration=None, steps=MOUSE_STEPS, jitter_px=MOUSE_JITTER,
                               click=True, button='left'):
    """
    Mueve el mouse en curva Bezier con easing y pequeño jitter, y realiza clic.
    """
    if total_duration is None:
        total_duration = random.uniform(MOUSE_MIN_TIME, MOUSE_MAX_TIME)

    start = pyautogui.position()
    p1, p2 = _random_ctrl_points(start, target_xy, curvature_px=120)

    t0 = time.time()
    for i in range(1, steps + 1):
        t = i / steps
        te = _ease_in_out_quad(t)
        x, y = _bezier_cubic(start, p1, p2, target_xy, te)
        x += random.uniform(-jitter_px, jitter_px)
        y += random.uniform(-jitter_px, jitter_px)
        pyautogui.moveTo(x, y, duration=0)
        elapsed = time.time() - t0
        target_time = te * total_duration
        sleep_left = max(0.0, target_time - elapsed)
        time.sleep(sleep_left)

    time.sleep(random.uniform(0.08, 0.22))
    if click:
        pyautogui.mouseDown(button=button)
        time.sleep(random.uniform(0.05, 0.12))
        pyautogui.mouseUp(button=button)


def human_click_element(driver, element, move_time=None, steps=MOUSE_STEPS, jitter_px=MOUSE_JITTER, button='left'):
    smooth_scroll_into_view(driver, element)
    time.sleep(random.uniform(0.15, 0.35))
    tx, ty = get_element_screen_center(driver, element)
    move_mouse_curve_and_click(
        (tx, ty),
        total_duration=move_time if move_time else random.uniform(MOUSE_MIN_TIME, MOUSE_MAX_TIME),
        steps=steps,
        jitter_px=jitter_px,
        click=True,
        button=button
    )

# ===================== Funciones Capsolver =====================
def capture_recaptcha_challenge(driver):
    """
    Captura la imagen completa de la cuadrícula del reCAPTCHA y extrae la pregunta.
    Retorna: (image_base64, question_text)
    """
    try:
        # Cambiar al iframe del desafío (bframe)
        driver.switch_to.default_content()
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
        )
        driver.switch_to.frame(iframe)
        
        # Esperar a que aparezca la cuadrícula de imágenes
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".rc-imageselect-target"))
        )
        
        # Extraer la pregunta del desafío
        question_element = driver.find_element(By.CSS_SELECTOR, ".rc-imageselect-desc-no-canonical")
        question_text = question_element.text.strip()
        log(f"[CAPTCHA] Pregunta extraída: {question_text}")
        
        # Capturar la imagen completa de la cuadrícula (no cuadrados individuales)
        table_element = driver.find_element(By.CSS_SELECTOR, ".rc-imageselect-table-33")
        log("[CAPTCHA] Capturando imagen completa de la cuadrícula...")
        
        # Tomar screenshot de toda la tabla/cuadrícula
        screenshot = table_element.screenshot_as_png
        image_base64 = base64.b64encode(screenshot).decode('utf-8')
        
                # AGREGAR ESTAS LÍNEAS PARA GUARDAR LA IMAGEN:
        try:
            # Crear nombre descriptivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Limpiar la pregunta para usarla en el nombre del archivo
            clean_question = re.sub(r'[^\w\s-]', '', question_text.replace('\n', ' '))[:50]
            clean_question = re.sub(r'\s+', '_', clean_question.strip())
            
            filename = f"captcha_grid_{timestamp}_{clean_question}.png"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            # Decodificar base64 y guardar imagen
            image_data = base64.b64decode(image_base64)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            log(f"[CAPTCHA] 💾 Imagen guardada: {filepath}")
        except Exception as e:
            log(f"[CAPTCHA] ⚠️ Error guardando imagen: {e}")
        
        log("[CAPTCHA] ✅ Imagen completa capturada y convertida a base64")
        
        log("[CAPTCHA] ✅ Imagen completa capturada y convertida a base64")
        
        # Volver al contenido principal
        driver.switch_to.default_content()
        
        return [image_base64], question_text  # Devolvemos lista con un elemento para compatibilidad
        
    except Exception as e:
        log(f"[CAPTCHA] ❌ Error capturando desafío: {e}")
        driver.switch_to.default_content()
        return None, None


def solve_with_capsolver(images_base64_list, question):
    """
    Envía UNA imagen (la cuadrícula completa) a Capsolver y retorna las coordenadas.
    """
    try:
        log(f"[CAPTCHA] 🚀 Enviando imagen completa a Capsolver...")
        
        # Validar que tengamos la imagen
        if not images_base64_list or len(images_base64_list) == 0:
            log("[CAPTCHA] ❌ Lista de imágenes vacía")
            return None
            
        # Extraer la imagen completa de la cuadrícula
        complete_image_base64 = images_base64_list[0]
        
        # Crear tarea con la estructura correcta de Capsolver
        task_data = {
            "clientKey": CAPSOLVER_API_KEY,
            "task": {
                "type": "ReCaptchaV2Classification",
                "imageBody": complete_image_base64,
                "question": question
            }
        }
        
                # AGREGAR ESTAS LÍNEAS PARA DEBUG:
        print("=" * 50)
        print("REQUEST A CAPSOLVER:")
        print(f"URL: {CAPSOLVER_URL}")
        print(f"clientKey: {CAPSOLVER_API_KEY}")
        print(f"task.type: {task_data['task']['type']}")
        print(f"task.question: {task_data['task']['question']}")
        print(f"task.imageBody (primeros 100 chars): {complete_image_base64[:100]}...")
        print(f"task.imageBody (longitud total): {len(complete_image_base64)} caracteres")
        print("=" * 50)

        # Enviar solicitud
        response = requests.post(CAPSOLVER_URL, json=task_data, timeout=30)
        result = response.json()
        
                
        # AGREGAR ESTA LÍNEA TAMBIÉN:
        print(f"RESPUESTA DE CAPSOLVER: {result}")
        print("=" * 50)
        
        if result.get('errorId') != 0:
            log(f"[CAPTCHA] ❌ Error creando tarea: {result.get('errorDescription')}")
            return None
            
        task_id = result.get('taskId')
        log(f"[CAPTCHA] 📝 Tarea creada: {task_id}")
        
        # Esperar resultado
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(2)
            
            result_data = {
                "clientKey": CAPSOLVER_API_KEY,
                "taskId": task_id
            }
            
            response = requests.post(CAPSOLVER_RESULT_URL, json=result_data, timeout=30)
            result = response.json()
            
            if result.get('status') == 'ready':
                solution = result.get('solution', {})
                
                # Capsolver devuelve coordenadas directamente
                if 'coordinates' in solution:
                    coordinates = solution['coordinates']
                    log(f"[CAPTCHA] ✅ Coordenadas recibidas: {coordinates}")
                    return coordinates
                else:
                    log(f"[CAPTCHA] ❌ Formato de solución desconocido: {solution}")
                    return None
                    
            elif result.get('status') == 'processing':
                log(f"[CAPTCHA] ⏳ Procesando... (intento {attempt + 1}/{max_attempts})")
            else:
                log(f"[CAPTCHA] ❌ Error en resultado: {result}")
                return None
                
        log("[CAPTCHA] ❌ Timeout esperando resultado de Capsolver")
        return None
        
    except Exception as e:
        log(f"[CAPTCHA] ❌ Error con Capsolver: {e}")
        return None

#def objects_to_coordinates(objects):
#    """
#    Convierte índices de objetos a coordenadas de clic.
#    Asume una cuadrícula 3x3 estándar.
#    """
#    coordinates = []
#    tile_width = 126  # Ancho aproximado de cada tile
#    tile_height = 126  # Alto aproximado de cada tile
#    
#    for obj_index in objects:
#        # Calcular posición en la cuadrícula (0-8 para 3x3)
#        row = obj_index // 3
#        col = obj_index % 3
#        
#        # Calcular coordenadas del centro del tile
#        x = col * tile_width + tile_width // 2
#        y = row * tile_height + tile_height // 2
#        
#        coordinates.append([x, y])
#    
#    return coordinates

def click_recaptcha_coordinates(driver, coordinates):
    """
    Hace clic en las coordenadas devueltas por Capsolver dentro del iframe.
    Las coordenadas de Capsolver son absolutas dentro de la imagen de la cuadrícula.
    """
    try:
        # Cambiar al iframe del desafío
        driver.switch_to.default_content()
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
        )
        driver.switch_to.frame(iframe)
        
        # Obtener el elemento de la tabla de imágenes
        table_element = driver.find_element(By.CSS_SELECTOR, ".rc-imageselect-table-33")
        
        log(f"[CAPTCHA] 🖱️ Haciendo clic en {len(coordinates)} coordenadas...")
        
        # Obtener las dimensiones y posición de la tabla para calcular offsets correctos
        table_rect = driver.execute_script("""
            var rect = arguments[0].getBoundingClientRect();
            return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
        """, table_element)
        
        for i, (x, y) in enumerate(coordinates):
            try:
                # Las coordenadas de Capsolver son relativas a la imagen completa
                # Calcular la posición relativa dentro del elemento tabla
                relative_x = x
                relative_y = y
                
                # Hacer clic usando ActionChains con offset desde la esquina superior izquierda de la tabla
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(driver)
                
                # Mover al elemento tabla y luego aplicar el offset
                actions.move_to_element_with_offset(table_element, relative_x, relative_y)
                actions.pause(random.uniform(0.1, 0.3))
                actions.click()
                actions.perform()
                
                log(f"[CAPTCHA] ✅ Clic {i+1} en coordenadas ({x}, {y})")
                time.sleep(random.uniform(0.2, 0.5))
                
            except Exception as e:
                log(f"[CAPTCHA] ❌ Error haciendo clic en ({x}, {y}): {e}")
        
        # Volver al contenido principal
        driver.switch_to.default_content()
        return True
        
    except Exception as e:
        log(f"[CAPTCHA] ❌ Error haciendo clics: {e}")
        driver.switch_to.default_content()
        return False

def click_verify_button(driver):
    """
    Hace clic en el botón Verificar del reCAPTCHA.
    """
    try:
        # Cambiar al iframe del desafío
        driver.switch_to.default_content()
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
        )
        driver.switch_to.frame(iframe)
        
        # Buscar y hacer clic en el botón verificar
        verify_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#recaptcha-verify-button"))
        )
        
        # Hacer clic humano en el botón
        from selenium.webdriver.common.action_chains import ActionChains
        actions = ActionChains(driver)
        actions.move_to_element(verify_button)
        actions.pause(random.uniform(0.1, 0.3))
        actions.click()
        actions.perform()
        
        log("[CAPTCHA] ✅ Botón Verificar presionado")
        
        # Volver al contenido principal
        driver.switch_to.default_content()
        time.sleep(2)
        
        return True
        
    except Exception as e:
        log(f"[CAPTCHA] ❌ Error haciendo clic en Verificar: {e}")
        driver.switch_to.default_content()
        return False

# Función principal que orquesta todo el proceso de solucion CatpCHA con CapSolver
def solve_recaptcha_automatically(driver):
    """
    Función principal que resuelve automáticamente el reCAPTCHA usando Capsolver.
    """
    try:
        log("[CAPTCHA] 🤖 Iniciando resolución automática del reCAPTCHA...")
        
        # Paso 1: Capturar imágenes y pregunta
        images_base64_list, question = capture_recaptcha_challenge(driver)
        if not images_base64_list or not question:
            log("[CAPTCHA] ❌ No se pudieron capturar las imágenes o pregunta")
            return False
        
        # Paso 2: Resolver con Capsolver
        coordinates = solve_with_capsolver(images_base64_list, question)
        if not coordinates:
            log("[CAPTCHA] ❌ Capsolver no devolvió coordenadas")
            return False
        
        # Paso 3: Hacer clics en las coordenadas
        if not click_recaptcha_coordinates(driver, coordinates):
            log("[CAPTCHA] ❌ Error haciendo clics en coordenadas")
            return False
        
        # Paso 4: Hacer clic en Verificar
        if not click_verify_button(driver):
            log("[CAPTCHA] ❌ Error haciendo clic en Verificar")
            return False
        
        # Paso 5: Esperar a que se resuelva
        time.sleep(3)
        
        # Verificar si se resolvió correctamente
        try:
            token = driver.execute_script(
                "return (window.grecaptcha && grecaptcha.getResponse) ? grecaptcha.getResponse() : ''"
            )
            if token:
                log(f"[CAPTCHA] ✅ reCAPTCHA resuelto automáticamente!")
                return True
            else:
                log("[CAPTCHA] ⚠️ Token no encontrado después de resolver")
                return False
        except Exception as e:
            log(f"[CAPTCHA] ⚠️ Error verificando token: {e}")
            return False
            
    except Exception as e:
        log(f"[CAPTCHA] ❌ Error en resolución automática: {e}")
        return False


# ===================== Selenium Driver =====================
def create_driver(headless=False):
    from webdriver_manager.chrome import ChromeDriverManager

    options = webdriver.ChromeOptions()
    # Para que pyautogui pueda mover el verdadero cursor, no usar headless:
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    # Quitar bandera webdriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


# ===================== Manejo de reCAPTCHA con Capsolver =====================
def wait_for_recaptcha_solved(driver, timeout=RECAPTCHA_TIMEOUT):
    """
    Detecta y resuelve automáticamente el reCAPTCHA usando Capsolver.
    Si falla, permite resolución manual como fallback con timeout separado.
    """
    start = time.time()
    
    try:
        # Verificar si hay reCAPTCHA presente
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
        if not any(f.is_displayed() for f in iframes):
            log("[CAPTCHA] 👍 No hay reCAPTCHA presente")
            return True
        
        # Verificar si ya está resuelto
        try:
            token = driver.execute_script(
                "return (window.grecaptcha && grecaptcha.getResponse) ? grecaptcha.getResponse() : ''"
            )
            if token:
                log("[CAPTCHA] ✅ reCAPTCHA ya resuelto")
                return True
        except Exception:
            pass
        
        log("[CAPTCHA] 🔍 reCAPTCHA detectado, intentando resolución automática...")
        
        # Intentar resolución automática con Capsolver (timeout más corto)
        auto_timeout = min(90, timeout // 2)  # Máximo 90s para automático
        auto_start = time.time()
        
        if solve_recaptcha_automatically(driver):
            elapsed = time.time() - start
            log(f"[CAPTCHA] ✅ reCAPTCHA resuelto automáticamente en {elapsed:.1f}s!")
            return True
        
        # Si falla la resolución automática, fallback a resolución manual
        auto_elapsed = time.time() - auto_start
        log(f"[CAPTCHA] ⚠️ Resolución automática falló después de {auto_elapsed:.1f}s")
        log("[CAPTCHA] Esperando resolución manual...")
        log("🟡 Por favor resuelve el CAPTCHA manualmente en la ventana del navegador...")
        
        def token_present(drv):
            try:
                token = drv.execute_script(
                    "return (window.grecaptcha && grecaptcha.getResponse) ? grecaptcha.getResponse() : ''"
                )
                if token:
                    return True
            except Exception:
                pass
            try:
                tas = drv.find_elements(By.CSS_SELECTOR, "textarea#g-recaptcha-response, textarea[name='g-recaptcha-response']")
                for ta in tas:
                    val = ta.get_attribute("value") or ""
                    if val.strip():
                        return True
            except Exception:
                pass
            return False
        
        # Timeout separado para resolución manual (mínimo 120 segundos)
        manual_timeout = max(120, timeout - auto_elapsed)
        WebDriverWait(driver, manual_timeout, poll_frequency=0.5).until(lambda d: token_present(d))
        
        elapsed = time.time() - start
        log(f"🟢 CAPTCHA resuelto manualmente (tardó {elapsed:.1f}s total). Continuando…")
        
        # Restablecer zoom si se aplicó
        try:
            driver.execute_script("document.body.style.zoom='1'")
        except Exception:
            pass
            
        return True
        
    except TimeoutException:
        total_elapsed = time.time() - start
        log(f"[CAPTCHA] ❌ Timeout después de {total_elapsed:.1f}s sin resolver el CAPTCHA")
        return False
    except Exception as e:
        log(f"[CAPTCHA] ❌ Error manejando reCAPTCHA: {e}")
        return False

# ===================== Interacciones de página =====================
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
    """
    Devuelve el <button> 'Consultar' aunque esté dentro de Shadow DOM.
    1) Intenta selectores clásicos (rápidos).
    2) Si no aparece, hace una búsqueda profunda recursiva por Shadow DOM.
    """
    waits = WebDriverWait(driver, timeout, poll_frequency=0.25)

    # Asegura contexto principal (por si entraste a un iframe antes)
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    # ---------- 1) Búsqueda clásica (rápida) ----------
    basic_candidates = [
        (By.XPATH, "//*[@id='sribody']//button[contains(@class,'cyan-btn') and .//span[normalize-space()='Consultar']]"),
        (By.XPATH, "//button[.//span[normalize-space()='Consultar']]"),
        (By.XPATH, "//*[@id='sribody']//button[contains(@class,'cyan-btn')]"),
        (By.CSS_SELECTOR, "#sribody button.cyan-btn.ui-button"),
        # Tu XPath exacto del botón:
        (By.XPATH, "//*[@id='sribody']/sri-root/div/div[2]/div/div/sri-consulta-ruc-web-app/div/sri-ruta-ruc/div[2]/div[1]/div[6]/div[2]/div/div[2]/div/button"),
    ]

    found_visible = []
    try:
        # Espera a que el app Angular esté en DOM (no crítico si falla)
        waits.until(EC.presence_of_element_located((By.CSS_SELECTOR, "sri-consulta-ruc-web-app")))
    except TimeoutException:
        pass

    for by, sel in basic_candidates:
        try:
            elems = driver.find_elements(by, sel)
            for e in elems:
                try:
                    # si el selector apunta al <span>, sube al <button>
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

    # ---------- 2) Búsqueda profunda (Shadow DOM) ----------
    # Recorre todos los shadow roots abiertos y busca un botón cuyo texto (o el de su <span>) sea "Consultar".
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
      // 1) Primero, botones directos
      const btns = root.querySelectorAll('button, .ui-button');
      for (const b of btns) {
        if (matchesText(b)) return closestButton(b) || b;
        const span = b.querySelector('span');
        if (matchesText(span)) return closestButton(span) || b;
      }
      // 2) Luego, recorrido general
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
                # Selenium a veces devuelve nodos que no son WebElement; normalmente funciona.
                # Verifica que sea clickeable
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        log("🔎 Consultar: encontrado via Shadow DOM")
                        return btn
                except Exception:
                    # Si falla la introspección, asumimos que es válido y lo retornamos
                    return btn
        except Exception as e:
            log(f"ShadowDOM search error: {e}")
        time.sleep(0.25)

    # Nada encontrado
    log("🔎 Consultar: no se encontró ni con selectores clásicos ni via Shadow DOM")
    return None


def prepare_for_captcha(driver, zoom=1.2):
    """
    Centra y resalta el iframe del reCAPTCHA, aumenta zoom y mueve el cursor cerca (sin clicar).
    No interactúa con la cuadrícula ni hace clics.
    """
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    # Busca el iframe del desafío (bframe)
    try:
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/bframe']"))
        )
    except TimeoutException:
        # Puede ser que salga la casilla primero; intenta ese iframe
        try:
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha']"))
            )
        except TimeoutException:
            log("⚠️ No se encontró iframe de reCAPTCHA para centrar/resaltar.")
            return

    # Resaltar y centrar el captcha, tambien se puede quitar el zoom devolviendo document.body.style.zoom='1' justo después de que el CAPTCHA se resuelva
    try:
        driver.execute_script("""
            arguments[0].scrollIntoView({block:'center'});
            arguments[0].style.outline = '3px solid #ff5252';
            document.body.style.zoom = arguments[1];
        """, iframe, str(zoom))
    except Exception as e:
        log(f"prepare_for_captcha: no se pudo aplicar outline/zoom: {e}")

    # Mover cursor CERCA del centro (sin hacer click)
    try:
        x, y = get_element_screen_center(driver, iframe)
        import pyautogui, time
        pyautogui.moveTo(x, y-120, duration=0.4)  # un poco arriba del centro
        # Beeps en Windows
        try:
            import sys, winsound
            if sys.platform.startswith("win"):
                for _ in range(2):
                    winsound.Beep(1200, 180)
                    time.sleep(0.12)
        except Exception:
            pass
    except Exception as e:
        log(f"prepare_for_captcha: no se pudo mover el cursor cerca: {e}")


def wait_for_results(driver) -> bool:
    """
    Espera a que aparezca algún contenedor con datos. Ajusta selectores si el DOM cambia.
    """
    try:
        container_xpaths = [
            "//div[contains(@class,'resultado') or contains(@id,'resultado')]",
            "//table[contains(@class,'tabla') or contains(@id,'tblResultado')]",
            "//div[contains(@class,'panel-body') and string-length(normalize-space(.))>50]",
            "//sri-mostrar-contribuyente",
        ]
        WebDriverWait(driver, RESULTS_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "|".join(container_xpaths)))
        )
        time.sleep(1.0)
        return True
    except TimeoutException:
        return False


# ===================== Parsing =====================
def parse_results(driver) -> Dict[str, str]:
    soup = BeautifulSoup(driver.page_source, "html.parser")
    extracted = {}

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cols = tr.find_all(["td", "th"])
            if len(cols) >= 2:
                k = cols[0].get_text(" ", strip=True)
                v = cols[1].get_text(" ", strip=True)
                if k and v:
                    extracted[k] = v

    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            k = dt.get_text(" ", strip=True)
            v = dd.get_text(" ", strip=True)
            if k and v:
                extracted[k] = v

    return extracted


# ===================== Lectura de RUCs =====================
def load_rucs_from_csv(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    rucs = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "ruc" not in reader.fieldnames:
            raise ValueError(f"El CSV {path} debe tener una columna 'ruc'.")
        for row in reader:
            r = (row.get("ruc") or "").strip()
            if r:
                rucs.append(r)
    return rucs


# ===================== Flujo por RUC =====================
def process_ruc(driver, ruc: str, cache: Dict[str, Dict]) -> Optional[Dict]:
    # ---- Detección por caché DESACTIVADA (comentada) ----
    # cached = cache_hit(cache, ruc)
    # if cached:
    #     log(f"✅ Cache HIT para RUC {ruc}. Omitiendo consulta al sitio.")
    #     return cached

    for attempt in range(1, MAX_RETRIES + 4):
        try:
            log(f"--- Procesando RUC {ruc} (intento {attempt}/{MAX_RETRIES}) ---")
            driver.get(SRI_URL)
            time.sleep(random.uniform(0.8, 1.6))

            # Input RUC
            ruc_input = find_ruc_input(driver)
            if not ruc_input:
                log("⚠️ No se encontró el input de RUC.")
                save_screenshot(driver, f"no_ruc_input_{ruc}.png")
                raise RuntimeError("Input RUC no encontrado")

            human_type(ruc_input, ruc)
            time.sleep(random.uniform(0.3, 0.7))

            # Botón Consultar
            btn = find_consultar_button(driver, timeout=20)
            if not btn:
                log("⚠️ No se encontró el botón 'Consultar'.")
                save_screenshot(driver, f"no_consultar_button_{ruc}.png")
                raise RuntimeError("Botón Consultar no encontrado")

            # ---------- Click humano + fallbacks ----------
            # 1) Click humano con cursor curvo
            try:
                human_click_element(driver, btn)
                time.sleep(random.uniform(0.2, 0.6))
            except Exception as e:
                log(f"⚠️ Falló human_click_element: {e}")

            # Verificar si el click surtió efecto
            time.sleep(random.uniform(0.6, 1.2))

            def _button_still_present():
                try:
                    return btn.is_displayed()
                except Exception:
                    return False

            if _button_still_present():
                # 2) ActionChains con pequeño offset
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(driver)
                    actions.move_to_element(btn)
                    actions.pause(random.uniform(0.12, 0.3))
                    actions.move_by_offset(random.randint(-3, 3), random.randint(-3, 3))
                    actions.pause(random.uniform(0.08, 0.2))
                    actions.click()
                    actions.perform()
                    time.sleep(random.uniform(0.4, 0.9))
                except Exception as e:
                    log(f"⚠️ Fallback ActionChains falló: {e}")

            if _button_still_present():
                # 3) JS click final como último recurso
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(random.uniform(0.1, 0.3))
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(random.uniform(0.4, 0.9))
                    log("✅ JS click ejecutado como fallback")
                except Exception as e:
                    log(f"❌ Fallback JS click falló: {e}")
            # ---------- fin bloque click ----------
            

            # Preparar el desafío para resolución automática/manual
            prepare_for_captcha(driver, zoom=1.2)
            
            # Manejar reCAPTCHA automáticamente o manualmente
            try:
                if not wait_for_recaptcha_solved(driver, timeout=RECAPTCHA_TIMEOUT):
                    log("❌ No se pudo resolver el reCAPTCHA")
                    save_screenshot(driver, f"recaptcha_failed_{ruc}.png")
                    raise RuntimeError("reCAPTCHA no resuelto")
            except Exception as e:
                log(f"❌ Error procesando reCAPTCHA: {e}")
                save_screenshot(driver, f"recaptcha_error_{ruc}.png")
                raise

            # Si aparece reCAPTCHA, tú lo resuelves; el script espera
            #try:
            #    has_recaptcha = False
            #    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            #    if any(f.is_displayed() for f in iframes):
            #        has_recaptcha = True
            #    token = ""
            #    try:
            #        token = driver.execute_script(
            #            "return (window.grecaptcha && grecaptcha.getResponse) ? grecaptcha.getResponse() : ''"
            #        )
            #    except Exception:
            #        pass
            #    if has_recaptcha and not token:
            #        wait_for_recaptcha_solved(driver, timeout=RECAPTCHA_TIMEOUT)
            #except Exception:
            #    pass

            
      
            # Si aparece reCAPTCHA, lo resuelves tú (HITL)
            #try:
            #    has_recaptcha = False
            #    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            #    if any(f.is_displayed() for f in iframes):
            #        has_recaptcha = True
            #    token = ""
            #    try:
            #       token = driver.execute_script(
            #           "return (window.grecaptcha && grecaptcha.getResponse) ? grecaptcha.getResponse() : ''"
            #        )
            #    except Exception:
            #        pass
            #    if has_recaptcha and not token:
            #        wait_for_recaptcha_solved(driver, timeout=RECAPTCHA_TIMEOUT)
            #except Exception:
            #    pass

            # Esperar resultados
            if not wait_for_results(driver):
                log("⏳ No aparecieron resultados a tiempo.")
                save_screenshot(driver, f"no_results_{ruc}.png")
                raise TimeoutException("Resultados no visibles")

            # Parsear
            data = parse_results(driver)
            if not data:
                log("⚠️ No se extrajo información.")
                save_screenshot(driver, f"no_data_{ruc}.png")
                raise RuntimeError("Extracción vacía")

            # Guardar CSV
            csv_path = os.path.join(OUTPUT_DIR, f"ruc_{ruc}.csv")
            rows = [["Field", "Value"]] + [[k, v] for k, v in data.items()]
            csv_write_rows(csv_path, rows)
            log(f"✅ Datos guardados: {csv_path}")

            # Guardar en caché (se mantiene para uso futuro si reactivas la detección)
            cache[ruc] = {"timestamp": datetime.now().isoformat(), "data": data}
            save_cache(cache)

            return data

        except Exception as e:
            log(f"❌ Error en intento {attempt} para RUC {ruc}: {e}")
            wait_s = min(8 * attempt, 20)  # backoff suave
            time.sleep(random.uniform(wait_s, wait_s + 2))

    log(f"🛑 Falló el procesamiento para RUC {ruc} tras {MAX_RETRIES} intentos.")
    return None


# ===================== Main =====================
def main():
    # 1) RUCs desde CSV (si existe rucs.csv con columna 'ruc')
    rucs = []
    try:
        rucs = load_rucs_from_csv(RUC_CSV)
        if rucs:
            log(f"📄 Cargados {len(rucs)} RUCs desde {RUC_CSV}")
    except Exception as e:
        log(f"CSV {RUC_CSV} ignorado: {e}")

    # 2) Si no hay CSV, usar lista fija
    if not rucs:
        rucs = [
            "2300531528001",   # ejemplo
            # agrega más RUCs aquí si no usarás CSV
        ]

    cache = load_cache()
    driver = create_driver(headless=False)  # visible: necesario para cursor real
    try:
        for idx, ruc in enumerate(rucs, 1):
            log(f"\n[{idx}/{len(rucs)}] RUC objetivo: {ruc}")
            _ = process_ruc(driver, ruc, cache)
            # descanso entre RUCs para no disparar anti-abuso
            time.sleep(random.uniform(3.5, 7.0))
        log("\n🏁 Proceso completado.")
    except KeyboardInterrupt:
        log("Interrupción por usuario.")
    except Exception as e:
        log(f"Error no controlado: {e}")
        traceback.print_exc()
    finally:
        driver.quit()
        


if __name__ == "__main__":
    main()
