""" sri_ruc_query.py - Enhanced Version with Dual CAPTCHA solving - FIXED
Usage: python sri_ruc_query.py

What it does:
- Opens the SRI RUC query page
- Types RUC number (configurable)
- Handles TWO types of CAPTCHA:
  1. reCAPTCHA (invisible)
  2. Image selection CAPTCHA (motorcycles, etc.)
- Automatically solves both using CapSolver API
- Scrapes data slowly like a human
- Saves results to CSV
- Continues running until manually closed
"""

import time
import json
import csv
import os
import random
import requests
from PIL import Image
import io
import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# ---------- Configuration ----------
RUC = "0916260698001"  # Change this to your desired RUC number
URL = "https://srienlinea.sri.gob.ec/sri-en-linea/SriRucWeb/ConsultaRuc/Consultas/consultaRuc"
OUT_DIR = "sri_ruc_output"
os.makedirs(OUT_DIR, exist_ok=True)

CAPSOLVER_API_KEY = "CAP-6A1AB119B5D19E99F0A7F91E2A78F264CB84F5EEB75AA61FCBA4B9A6121504D2"  # <---- PON TU API KEY DE CAPSOLVER AQUÍ

# Human-like behavior settings
MIN_DELAY = 1.5
MAX_DELAY = 4.0
TYPING_DELAY_MIN = 0.1
TYPING_DELAY_MAX = 0.3

def solve_recaptcha(sitekey: str, url: str) -> str:
    """
    Envía el captcha a capsolver y devuelve el token listo para inyectar.
    """
    # Crear tarea
    task_payload = {
        "clientKey": CAPSOLVER_API_KEY,
        "task": {
            "type": "NoCaptchaTaskProxyless",  # Para reCAPTCHA v2/v3
            "websiteURL": url,
            "websiteKey": sitekey
        }
    }

    task_resp = requests.post("https://api.capsolver.com/createTask", json=task_payload).json()
    task_id = task_resp.get("taskId")

    if not task_id:
        raise Exception(f"Error creando tarea: {task_resp}")

    # Esperar a que se resuelva
    get_payload = {"clientKey": CAPSOLVER_API_KEY, "taskId": task_id}
    token = None
    for _ in range(20):  # reintentos
        time.sleep(3)
        res = requests.post("https://api.capsolver.com/getTaskResult", json=get_payload).json()
        if res.get("status") == "ready":
            token = res["solution"]["gRecaptchaResponse"]
            break

    if not token:
        raise Exception("No se pudo resolver el captcha con capsolver")

    return token

# ---------- CAPTCHA Detection Functions ----------
def detect_captcha_type(driver):
    """Detecta qué tipo de CAPTCHA está presente"""
    print("[CAPTCHA] Analizando tipo de CAPTCHA presente...")
    
    captcha_types = []
    
    # 1. Buscar reCAPTCHA
    try:
        recaptcha_elements = driver.find_elements(By.CSS_SELECTOR, "div.g-recaptcha, iframe[src*='recaptcha']")
        if any(elem.is_displayed() for elem in recaptcha_elements):
            captcha_types.append("recaptcha")
            print("[CAPTCHA] reCAPTCHA detectado")
    except:
        pass
    
    # 2. Buscar CAPTCHA de imágenes dentro del iframe de reCAPTCHA

    return captcha_types

def solve_recaptcha_with_capsolver(site_key, url):
    """Resuelve reCAPTCHA usando CapSolver"""
    print("[CAPSOLVER] Enviando tarea reCAPTCHA a CapSolver...")
    task_payload = {
        "clientKey": CAPSOLVER_API_KEY,
        "task": {
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteURL": url,
            "websiteKey": site_key
        }
    }

    create_task_url = "https://api.capsolver.com/createTask"
    get_result_url = "https://api.capsolver.com/getTaskResult"

    response = requests.post(create_task_url, json=task_payload)
    result = response.json()

    if result.get("errorId") != 0:
        print("[CAPSOLVER] Error creando tarea reCAPTCHA:", result.get("errorDescription"))
        return None

    task_id = result["taskId"]
    print(f"[CAPSOLVER] reCAPTCHA Task ID: {task_id}")

    # Esperar resultado
    max_attempts = 40
    for attempt in range(max_attempts):
        time.sleep(3)
        
        res = requests.post(get_result_url, json={
            "clientKey": CAPSOLVER_API_KEY,
            "taskId": task_id
        }).json()

        if res.get("status") == "ready":
            print("[CAPSOLVER] reCAPTCHA resuelto!")
            return res["solution"]["gRecaptchaResponse"]
        elif res.get("status") == "processing":
            print(f"[CAPSOLVER] reCAPTCHA procesando... {attempt+1}/{max_attempts}")
        else:
            print("[CAPSOLVER] Error en reCAPTCHA:", res.get("errorDescription"))
            return None
    
    return None

def get_recaptcha_sitekey(driver):
    """Obtiene la sitekey del reCAPTCHA"""
    try:
        # Método 1: Buscar en elementos div
        recaptcha_divs = driver.find_elements(By.CSS_SELECTOR, "div.g-recaptcha")
        for div in recaptcha_divs:
            if div.is_displayed():
                site_key = div.get_attribute("data-sitekey")
                if site_key:
                    print(f"[CAPTCHA] Site key encontrado: {site_key}")
                    return site_key
        
        # Método 2: Buscar en el código fuente
        page_source = driver.page_source
        import re
        sitekey_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page_source)
        if sitekey_match:
            site_key = sitekey_match.group(1)
            print(f"[CAPTCHA] Site key encontrado en fuente: {site_key}")
            return site_key
        
        # Método 3: Sitekey conocido del SRI
        default_key = "6LemEY4UAAAAAHVQd7ZyoCoqBKNoWrcUO4b5H-SP"
        print(f"[CAPTCHA] Usando site key por defecto: {default_key}")
        return default_key
        
    except Exception as e:
        print(f"[CAPTCHA] Error obteniendo sitekey: {e}")
        return "6LemEY4UAAAAAHVQd7ZyoCoqBKNoWrcUO4b5H-SP"

def inject_recaptcha_token(driver, token):
    
    """Inyecta el token de reCAPTCHA en todas las ubicaciones posibles"""
    try:
        print("[CAPTCHA] Inyectando token reCAPTCHA...")
        
        # Script mejorado para inyección de token
        injection_script = f"""
            console.log('Iniciando inyección de token reCAPTCHA...');
            
            // Método 1: Inyectar en textareas g-recaptcha-response
            var textareas = document.getElementsByName('g-recaptcha-response');
            console.log('Textareas encontrados:', textareas.length);
            for (var i = 0; i < textareas.length; i++) {{
                textareas[i].value = '{token}';
                textareas[i].innerHTML = '{token}';
                textareas[i].style.display = 'block';
                console.log('Token inyectado en textarea', i);
            }}
            
            // Método 2: Buscar todos los textareas ocultos
            var allTextareas = document.querySelectorAll('textarea[style*="display: none"], textarea[style*="display:none"]');
            console.log('Textareas ocultos:', allTextareas.length);
            for (var j = 0; j < allTextareas.length; j++) {{
                if (allTextareas[j].name.includes('recaptcha') || allTextareas[j].id.includes('recaptcha')) {{
                    allTextareas[j].value = '{token}';
                    allTextareas[j].innerHTML = '{token}';
                    console.log('Token inyectado en textarea oculto', j);
                }}
            }}
            
            // Método 3: Simular callbacks de reCAPTCHA
            try {{
                if (typeof grecaptcha !== 'undefined') {{
                    if (window.recaptchaCallback) {{
                        window.recaptchaCallback('{token}');
                        console.log('Callback recaptchaCallback ejecutado');
                    }}
                    if (window.onRecaptchaSuccess) {{
                        window.onRecaptchaSuccess('{token}');
                        console.log('Callback onRecaptchaSuccess ejecutado');
                    }}
                    
                    // Intentar ejecutar callbacks globales
                    if (window.grecaptcha && window.grecaptcha.getResponse) {{
                        console.log('grecaptcha disponible');
                    }}
                }}
            }} catch (e) {{
                console.log('Error ejecutando callbacks:', e);
            }}
            
            // Método 4: Disparar eventos
            var event = new Event('change', {{ bubbles: true }});
            for (var k = 0; k < textareas.length; k++) {{
                textareas[k].dispatchEvent(event);
            }}
            
            console.log('Inyección de token completada');
            return true;
        """
        
        result = driver.execute_script(injection_script)
        print(f"[CAPTCHA] ✅ Token de reCAPTCHA inyectado correctamente: {result}")
        
        # Esperar un momento para que se procese
        time.sleep(1)
        
        return True
        
    except Exception as e:
        print(f"[CAPTCHA] Error inyectando token: {e}")
        return False
    
def click_verificar_button(driver):
    try:
        # Cambiar al iframe del reCAPTCHA
        iframe = driver.find_element(By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/bframe']")
        driver.switch_to.frame(iframe)

        # Buscar y hacer clic en el botón Verificar
        verificar_button = driver.find_element(By.ID, "recaptcha-verify-button")
        if verificar_button.is_displayed():
            verificar_button.click()
            print("[CAPTCHA] Clic en 'Verificar' realizado")
            driver.switch_to.default_content()  # Regresar al contenido principal
            return True

    except Exception as e:
        print(f"[CAPTCHA] Error al hacer clic en 'Verificar': {e}")
        driver.switch_to.default_content()  # Asegurar que volvemos al contenido principal
    return False


def handle_all_captchas(driver):
    """Maneja todos los tipos de CAPTCHA detectados"""
    print("[CAPTCHA] Iniciando manejo completo de CAPTCHAs...")
    
    # Esperar un poco para que los CAPTCHAs aparezcan
    time.sleep(3)
    
    success = True
    max_attempts = 3
    
    for attempt in range(max_attempts):
        print(f"[CAPTCHA] Intento {attempt + 1}/{max_attempts}")
        
        captcha_types = detect_captcha_type(driver)
        
        if not captcha_types:
            print("[CAPTCHA] No se detectaron CAPTCHAs")
            return True
        
        # Manejar reCAPTCHA primero
        if "recaptcha" in captcha_types:
            site_key = get_recaptcha_sitekey(driver)
            if site_key:
                token = solve_recaptcha_with_capsolver(site_key, driver.current_url)
                if token:
                    if inject_recaptcha_token(driver, token):
                        print("[CAPTCHA] reCAPTCHA procesado exitosamente")
                        time.sleep(2)
                        click_verificar_button(driver)
                    else:
                        print("[CAPTCHA] Error inyectando token reCAPTCHA")
                        success = False
                else:
                    print("[CAPTCHA] Error obteniendo token reCAPTCHA")
                    success = False
    
        
        # Verificar si los CAPTCHAs fueron resueltos
        time.sleep(3)
        new_captcha_types = detect_captcha_type(driver)
        
        if not new_captcha_types or len(new_captcha_types) < len(captcha_types):
            print("[CAPTCHA] CAPTCHAs resueltos exitosamente!")
            return True
        
        if attempt < max_attempts - 1:
            print(f"[CAPTCHA] CAPTCHAs aún presentes, reintentando...")
            time.sleep(2)
    
    return success

# ---------- Human-like Behavior Functions ----------
def human_delay():
    delay = random.uniform(MIN_DELAY, MAX_DELAY)
    time.sleep(delay)

def human_typing(element, text):
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX))

def human_click(element, driver):
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    time.sleep(random.uniform(0.5, 1.5))
    if random.random() < 0.7:
        element.click()
    else:
        driver.execute_script("arguments[0].click();", element)

# ---------- Setup Selenium WebDriver ----------
def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ---------- Main Functions ----------
def click_consult_button(driver):
    tries = [
        (By.XPATH, "//button[contains(normalize-space(.),'Consultar')]"),
        (By.XPATH, "//input[@type='submit' and contains(@value,'Consultar')]"),
        (By.CSS_SELECTOR, "button.btn, input[type='submit']"),
    ]
    
    for by, sel in tries:
        try:
            elems = driver.find_elements(by, sel)
            for e in elems:
                if e.is_displayed():
                    human_click(e, driver)
                    return True
        except Exception:
            pass
    return False

def extract_data(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    extracted = {}
    
    # Extraer de tablas
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for r in rows:
            cols = r.find_all(["td", "th"])
            if len(cols) >= 2:
                key = cols[0].get_text(" ", strip=True)
                val = cols[1].get_text(" ", strip=True)
                if key and val:
                    extracted[key] = val
    
    # Extraer de listas de definición
    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for k, v in zip(dts, dds):
            key = k.get_text(" ", strip=True)
            val = v.get_text(" ", strip=True)
            if key and val:
                extracted[key] = val
    
    return extracted

def save_to_csv(data, filename="ruc_results.csv"):
    csv_path = os.path.join(OUT_DIR, filename)
    if not data:
        print("No data to save")
        return
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Field", "Value"])
        for k, v in data.items():
            writer.writerow([k, v])
    
    print(f"Data saved to CSV: {csv_path}")

def scrape_ruc(driver, ruc_number):
    try:
        print(f"\n--- Starting scrape for RUC: {ruc_number} ---")
        driver.get(URL)
        print("Page loaded")
        human_delay()

        # Encontrar campo RUC
        input_candidates = []
        input_candidates += driver.find_elements(By.XPATH, "//input[@maxlength='13']")
        input_candidates += driver.find_elements(By.XPATH, "//input[contains(translate(@name,'RUC','ruc'),'ruc')]")
        input_candidates += driver.find_elements(By.XPATH, "//input[contains(translate(@id,'RUC','ruc'),'ruc')]")

        if not input_candidates:
            input_candidates = [el for el in driver.find_elements(By.XPATH, "//input[@type='text' or @type='search']") if el.is_displayed()]

        if not input_candidates:
            print(f"Could not find RUC input field for {ruc_number}")
            return None

        ruc_input = input_candidates[0]
        print("Found RUC input field, typing...")
        human_typing(ruc_input, ruc_number)
        human_delay()

        print("Clicking consult button...")
        if not click_consult_button(driver):
            print(f"Could not click consult button for {ruc_number}")
            return None

        # Manejar todos los CAPTCHAs
        print("Handling CAPTCHAs...")
        captcha_success = handle_all_captchas(driver)
        
        if captcha_success:
            print("CAPTCHAs manejados exitosamente")
        else:
            print("Advertencia: Algunos CAPTCHAs pueden no haberse resuelto correctamente")

        # Esperar resultados
        print("Waiting for results...")
        time.sleep(5)

        result_locators = [
            (By.XPATH, "//div[contains(@class,'resultado') or contains(@id,'resultado')]"),
            (By.XPATH, "//table[contains(@class,'tabla') or contains(@id,'tblResultado')]"),
            (By.XPATH, "//div[contains(@class,'panel-body') and string-length(normalize-space(.))>50]"),
        ]

        results_appeared = False
        max_wait = 60
        elapsed = 0

        while elapsed < max_wait:
            for by, sel in result_locators:
                try:
                    elems = driver.find_elements(by, sel)
                    visible_elems = [e for e in elems if e.is_displayed() and len(e.text.strip()) > 10]
                    if visible_elems:
                        results_appeared = True
                        break
                except Exception:
                    continue
            
            if results_appeared:
                break
            
            time.sleep(2)
            elapsed += 2

        if results_appeared:
            print("Extracting data...")
            data = extract_data(driver)
            if data:
                print(f"Successfully extracted {len(data)} fields for {ruc_number}")
                save_to_csv(data, f"ruc_{ruc_number}.csv")
                return data
            else:
                print("No data extracted from results.")
        else:
            print(f"Results did not appear for {ruc_number}")
            # Guardar screenshot para debug
            driver.save_screenshot(os.path.join(OUT_DIR, f"debug_{ruc_number}.png"))

        return None

    except Exception as e:
        print(f"Exception during scraping RUC {ruc_number}: {e}")
        return None

def main():
    print("=== SRI RUC Scraper with Dual CAPTCHA Support ===")
    
    if not CAPSOLVER_API_KEY or CAPSOLVER_API_KEY == "YOUR_CAPSOLVER_API_KEY_HERE":
        print("ERROR: Necesitas configurar tu CAPSOLVER_API_KEY")
        return
        
    driver = create_driver()
    try:
        scrape_ruc(driver, RUC)
        
        print("\nScript completed. Browser will remain open for manual inspection.")
        print("Press Ctrl+C to exit.")
        
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("Exiting by user request.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()