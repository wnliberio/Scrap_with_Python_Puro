# core/pages/denuncias_page.py
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from ..utils.log import log
from ..config import RESULTS_TIMEOUT

def find_name_input(driver):
    """
    Input de nombres completos (hasta 50 caracteres).
    Principal: #pwd  (XPath: //*[@id="pwd"])
    """
    try:
        el = driver.find_element(By.CSS_SELECTOR, "#pwd")
        if el.is_displayed():
            return el
    except Exception:
        pass

    # Fallbacks simples
    for el in driver.find_elements(By.XPATH, "//input[@id='pwd' or @name='pwd']"):
        try:
            if el.is_displayed():
                return el
        except Exception:
            continue
    return None

def find_search_button(driver, timeout=15):
    """
    Botón 'Buscar Denuncia'
    Principal: #btn_buscar_denuncia  (XPath: //*[@id='btn_buscar_denuncia'])
    """
    end = time.time() + timeout

    # Selectores directos
    direct = [
        (By.CSS_SELECTOR, "#btn_buscar_denuncia"),
        (By.XPATH, "//*[@id='btn_buscar_denuncia']"),
        # por si el valor del input se usa:
        (By.XPATH, "//input[@type='button' and @value='Buscar Denuncia']"),
    ]
    while time.time() < end:
        for by, sel in direct:
            try:
                btns = driver.find_elements(by, sel)
                for b in btns:
                    if b.is_displayed() and b.is_enabled():
                        return b
            except Exception:
                continue
        time.sleep(0.25)

    log("🔎 Denuncias: botón 'Buscar Denuncia' no encontrado")
    return None

def wait_for_denuncias_results(driver, timeout=RESULTS_TIMEOUT) -> bool:
    """
    Espera a que aparezcan los resultados de denuncias con validaciones múltiples.
    """
    start_time = time.time()
    
    try:
        # 1. Espera inicial más corta para que Angular procese
        time.sleep(1.5)
        
        # 2. Primero espera que el contenedor #resultados exista
        log("🔍 Esperando contenedor #resultados...")
        WebDriverWait(driver, min(10, timeout)).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#resultados"))
        )
        log("✅ Contenedor #resultados encontrado")
        
        # 3. Función de validación más robusta
        def has_meaningful_content(drv):
            try:
                # Buscar el contenedor principal
                resultados = drv.find_element(By.CSS_SELECTOR, "#resultados")
                
                # Verificar si ya no está el loading
                loading_elements = drv.find_elements(By.CSS_SELECTOR, "#loading, .loading, [id*='loading']")
                for loading in loading_elements:
                    if loading.is_displayed():
                        return False
                
                # Verificar estructura específica del HTML que vemos
                checks = [
                    # Buscar divs con clase 'general' que contienen las tablas
                    "div.general",
                    # Buscar tablas directamente
                    "#resultados table",
                    # Buscar botones de acciones (Limpiar Campo, Limpiar Pantalla)
                    "input[value*='Limpiar']",
                    # Buscar cualquier contenido estructurado
                    "#resultados div[style*='display: block']"
                ]
                
                content_found = False
                for selector in checks:
                    elements = drv.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        try:
                            if el.is_displayed():
                                # Para tablas, verificar que tengan contenido
                                if el.tag_name.lower() == 'table':
                                    rows = el.find_elements(By.TAG_NAME, "tr")
                                    if len(rows) > 1:  # Más que solo header
                                        content_found = True
                                        break
                                # Para otros elementos, verificar texto o HTML
                                elif (el.text and len(el.text.strip()) > 10) or \
                                     (el.get_attribute("innerHTML") and len(el.get_attribute("innerHTML")) > 50):
                                    content_found = True
                                    break
                        except Exception:
                            continue
                    if content_found:
                        break
                
                if content_found:
                    log("✅ Contenido estructurado encontrado")
                    return True
                
                # Verificación adicional por texto general
                body_text = drv.execute_script("return document.body.innerText || ''").lower()
                result_keywords = [
                    "resultado", "denuncias", "consulta realizada", 
                    "datos encontrados", "información", "limpiar campo"
                ]
                
                if any(keyword in body_text for keyword in result_keywords):
                    log("✅ Palabras clave de resultados encontradas")
                    return True
                
                return False
                
            except Exception as e:
                log(f"❌ Error verificando contenido: {e}")
                return False
        
        # 4. Esperar con timeout ajustado
        remaining_time = timeout - (time.time() - start_time)
        if remaining_time <= 0:
            return False
            
        log(f"🔍 Esperando contenido significativo... (timeout restante: {remaining_time:.1f}s)")
        WebDriverWait(driver, remaining_time, poll_frequency=0.5).until(
            lambda d: has_meaningful_content(d)
        )
        
        # 5. Estabilización final
        time.sleep(1.0)
        log("✅ Resultados de denuncias detectados correctamente")
        return True
        
    except TimeoutException:
        log("⏰ Timeout esperando resultados de denuncias")
        # Debug: mostrar qué hay en #resultados
        try:
            resultados = driver.find_element(By.CSS_SELECTOR, "#resultados")
            content_preview = (resultados.text or "")[:200]
            html_preview = (resultados.get_attribute("innerHTML") or "")[:300]
            log(f"📋 Contenido actual (texto): {content_preview}")
            log(f"📋 Contenido actual (HTML): {html_preview}")
        except Exception as e:
            log(f"❌ No se pudo obtener debug info: {e}")
        return False
        
    except Exception as e:
        log(f"❌ Error inesperado en wait_for_denuncias_results: {e}")
        return False