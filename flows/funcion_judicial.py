# flows/funcion_judicial.py
import time
import random
from typing import Optional, Dict

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, JavascriptException

from core.browser import create_driver
from core.utils.log import log
# from core.io import cache as cache_io  # ⟵ eliminado
from core.utils.screenshot import save_fullpage_png, save_element_screenshot_png, save_scrollable_container_png
from core.human import human_type, human_click_element
from core.config import MAX_RETRIES

RESULTS_CONTAINER_SELECTOR = (
    "body > app-root > app-expel-listado-juicios > expel-sidenav > "
    "mat-sidenav-container > mat-sidenav-content > section"
)
FUNCION_JUDICIAL_URL = "https://procesosjudiciales.funcionjudicial.gob.ec/busqueda-filtros"


def _slug(text: str) -> str:
    """Genera un slug para nombres de archivo"""
    import re
    return re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '_').lower()


def _wait(driver, secs: float):
    """Espera con variación humana"""
    time.sleep(random.uniform(secs * 0.8, secs * 1.2))


# ===== HELPERS DE SCROLL =====
def _element_scroll_height(driver, element) -> int:
    try:
        return driver.execute_script("return arguments[0].scrollHeight || 0;", element) or 0
    except JavascriptException:
        return 0


def _element_scroll_top(driver, element) -> int:
    try:
        return driver.execute_script("return arguments[0].scrollTop || 0;", element) or 0
    except JavascriptException:
        return 0


def _scroll_element_step(driver, element, delta: int) -> int:
    """Mueve scrollTop por 'delta' y devuelve el nuevo scrollTop"""
    try:
        return driver.execute_script(
            "arguments[0].scrollTop = Math.max(0, arguments[0].scrollTop + arguments[1]); return arguments[0].scrollTop;",
            element, delta
        ) or 0
    except JavascriptException:
        return 0


def _scroll_window_to(driver, y: int):
    try:
        driver.execute_script("window.scrollTo(0, totalHeight + 200);")
    except JavascriptException:
        pass


def _smooth_cycle_scroll(driver, container=None, step: int = 500, max_loops: int = 60):
    """
    Hace un ciclo: bajar hasta el fondo, subir hasta arriba, bajar ~1/3, volver al tope.
    Usa contenedor si existe; si no, scroll de ventana.
    """
    if container:
        log("🧭 Scroll en contenedor de resultados (element.scrollTop)")
        # Asegurar top
        _scroll_element_step(driver, container, -10_000_000)
        _wait(driver, 0.3)

        # Down hasta el fondo
        loops = 0
        last_top = -1
        while loops < max_loops:
            top_before = _element_scroll_top(driver, container)
            _scroll_element_step(driver, container, step)
            _wait(driver, 0.05)
            top_after = _element_scroll_top(driver, container)
            if top_after == top_before or abs(top_after - last_top) < 5:
                break
            last_top = top_after
            loops += 1

        _wait(driver, 0.4)

        # Up hasta el tope
        loops = 0
        while loops < max_loops:
            top_before = _element_scroll_top(driver, container)
            _scroll_element_step(driver, container, -step)
            _wait(driver, 0.05)
            top_after = _element_scroll_top(driver, container)
            if top_after == 0 or top_after >= top_before:
                break
            loops += 1

        _wait(driver, 0.3)

        # Bajar un poco (~1/3 de pantalla)
        _scroll_element_step(driver, container, step // 3)
        _wait(driver, 0.25)

        # Volver al tope otra vez para el screenshot
        _scroll_element_step(driver, container, -10_000_000)
        _wait(driver, 0.35)

    else:
        log("🧭 Scroll a nivel de ventana (window.scrollTo)")
        # Top
        _scroll_window_to(driver, 0)
        _wait(driver, 0.3)

        # Down hasta el fondo
        try:
            doc_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);") or 0
        except JavascriptException:
            doc_height = 0

        y = 0
        loops = 0
        viewport = 800
        while loops < max_loops and y < doc_height:
            y += step
            _scroll_window_to(driver, y)
            _wait(driver, 0.05)
            loops += 1

        _wait(driver, 0.4)

        # Up hasta el tope
        loops = 0
        while loops < max_loops and y > 0:
            y -= step
            if y < 0:
                y = 0
            _scroll_window_to(driver, y)
            _wait(driver, 0.05)
            loops += 1

        _wait(driver, 0.3)

        # Bajar un poco y volver al tope
        _scroll_window_to(driver, viewport // 3)
        _wait(driver, 0.25)
        _scroll_window_to(driver, 0)
        _wait(driver, 0.35)


# ===== FINDERS =====
def find_name_input(driver, timeout: int = 15):
    """Encuentra el campo de nombres (#mat-input-4)"""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "mat-input-4"))
        )
    except TimeoutException:
        try:
            return WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="mat-input-4"]'))
            )
        except TimeoutException:
            return None


def find_search_button(driver, timeout: int = 15):
    """Encuentra el botón de búsqueda"""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.boton-buscar.mdc-button.mdc-button--raised.mat-mdc-raised-button.mat-accent.mat-mdc-button-base"))
        )
    except TimeoutException:
        try:
            return WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-expel-filtros-busqueda/expel-sidenav/mat-sidenav-container/mat-sidenav-content/section/form/div[6]/button[1]'))
            )
        except TimeoutException:
            return None


def find_results_section(driver, timeout: int = 10):
    """Encuentra la sección de resultados"""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, RESULTS_CONTAINER_SELECTOR))
        )
    except TimeoutException:
        try:
            return WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '/html/body/app-root/app-expel-listado-juicios/expel-sidenav/mat-sidenav-container/mat-sidenav-content/section'))
            )
        except TimeoutException:
            return None


def find_next_button(driver, timeout: int = 10):
    """Encuentra el botón 'Siguiente' con múltiples estrategias"""
    try:
        # Estrategia 1: Botón específico de siguiente
        return WebDriverWait(driver, timeout//3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.mat-mdc-paginator-navigation-next"))
        )
    except TimeoutException:
        try:
            # Estrategia 2: Por aria-label
            return WebDriverWait(driver, timeout//3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label*='Next']"))
            )
        except TimeoutException:
            try:
                # Estrategia 3: Cualquier botón que contenga ">" o "siguiente"
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        text = btn.get_attribute("innerHTML") or ""
                        aria_label = btn.get_attribute("aria-label") or ""
                        if (">" in text or "next" in text.lower() or "siguiente" in text.lower() or 
                            "next" in aria_label.lower() or "siguiente" in aria_label.lower()):
                            return btn
                return None
            except Exception:
                return None
def detect_no_results(driver) -> bool:
    """Detecta si aparece 'La consulta no devolvió resultados'"""
    try:
        body_text = driver.execute_script("return document.body.innerText || ''").lower()
        return any(phrase in body_text for phrase in [
            "la consulta no devolvió resultados",
            "no devolvió resultados",
            "sin resultados",
            "no se encontraron resultados"
        ])
    except Exception:
        return False


def detect_results_loaded(driver) -> bool:
    """Detecta si los resultados se cargaron correctamente"""
    try:
        results_section = find_results_section(driver, timeout=2)
        if results_section:
            body_text = driver.execute_script("return document.body.innerText || ''").lower()
            success_indicators = [
                "registros encontrados",
                "items por página",
                "página 1 de",
                "fecha de ingreso",
                "no. proceso",
                "acción /infracción",
                "detalle"
            ]
            found_indicators = sum(1 for indicator in success_indicators if indicator in body_text)
            if found_indicators >= 3:
                log(f"✅ Función Judicial: Detectados {found_indicators} indicadores de resultados exitosos")
                return True
        return False
    except Exception:
        return False


# ===== PROCESO PRINCIPAL =====
def process_funcion_judicial_once(apellidos_nombres: str, headless: bool = False) -> Optional[Dict]:
    """
    Ejecuta una consulta en Función Judicial (un solo intento).
    Sigue el patrón estándar process_[página]_once usado en el proyecto.
    """
    driver = None
    try:
        log(f"🏛️ Iniciando consulta Función Judicial para: {apellidos_nombres}")

        # 1. Crear driver y navegar
        driver = create_driver(headless=headless)
        driver.get(FUNCION_JUDICIAL_URL)
        _wait(driver, random.uniform(2.0, 4.0))

        # 2. Encontrar campo de nombre
        name_input = find_name_input(driver)
        if not name_input:
            log("❌ Función Judicial: no se encontró el campo de nombres")
            return None

        # 3. Escribir apellidos y nombres de forma humana
        log(f"✏️ Escribiendo: {apellidos_nombres}")
        name_input.clear()
        _wait(driver, 0.5)
        human_type(name_input, apellidos_nombres)
        _wait(driver, random.uniform(0.5, 1.0))

        # 4. Encontrar botón de búsqueda
        search_btn = find_search_button(driver)
        if not search_btn:
            log("❌ Función Judicial: no se encontró el botón de búsqueda")
            return None

        # 5. LÓGICA ESPECIAL: 3 clics con pausa
        log("🔍 Ejecutando secuencia de búsqueda especial...")
        screenshots_paths = []

        for click_num in range(1, 4):  # 3 clics máximo
            log(f"🖱️ Clic #{click_num}")
            try:
                if click_num == 1:
                    log("📍 Clic #1: En botón BUSCAR")
                    human_click_element(driver, search_btn)
                elif click_num == 2:
                    log("📍 Clic #2: En ventanita (75px arriba del botón)")
                    actions = ActionChains(driver)
                    actions.move_to_element_with_offset(search_btn, 0, -75).click().perform()
                elif click_num == 3:
                    log("📍 Clic #3: Nuevamente en botón BUSCAR")
                    human_click_element(driver, search_btn)
            except Exception as e:
                log(f"⚠️ Falló clic #{click_num}: {e}")
                try:
                    if click_num in (1, 3):
                        driver.execute_script("arguments[0].click();", search_btn)
                    elif click_num == 2:
                        driver.execute_script("""
                            var rect = arguments[0].getBoundingClientRect();
                            var x = rect.left + rect.width/2;
                            var y = rect.top + rect.height/2 - 75;
                            var elem = document.elementFromPoint(x, y);
                            if (elem) elem.click();
                        """, search_btn)
                except Exception as e2:
                    log(f"❌ Fallback JS click también falló: {e2}")

            _wait(driver, 1.0)

            if detect_results_loaded(driver):
                log(f"✅ Resultados detectados después del clic #{click_num}")
                break
            elif detect_no_results(driver):
                log(f"ℹ️ 'Sin resultados' detectado después del clic #{click_num}")
                break
            else:
                log(f"⏳ Sin cambios después del clic #{click_num}, continuando...")

        # 6. Si hay resultados, esperar y capturar sección específica
        if detect_results_loaded(driver):
            log("⏳ Esperando carga completa para captura específica...")
            _wait(driver, random.uniform(3.0, 5.0))

        # 7. Capturar específicamente la sección de resultados
        screenshot_1 = capture_results_section(
            driver, 
            f"funcion_judicial_{_slug(apellidos_nombres)}_resultados"
        )
        screenshots_paths.append(screenshot_1)
        log(f"📸 Screenshot de resultados guardado: {screenshot_1}")

        # 8. Si NO hay resultados, terminar aquí
        if detect_no_results(driver):
            log("ℹ️ Consulta sin resultados, finalizando")
            return {
                "screenshot_path": screenshots_paths[0] if screenshots_paths else None,
            }

        # 9. Para segunda página (si existe), hacer lo mismo
        if detect_results_loaded(driver):
            next_btn = find_next_button(driver)
            if next_btn:
                log("➡️ Navegando a página siguiente")
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
                    _wait(driver, 1.0)
                    
                    human_click_element(driver, next_btn)
                    _wait(driver, random.uniform(3.0, 5.0))
                    
                    # Capturar segunda página también con el contenedor específico
                    screenshot_2 = capture_results_section(
                        driver, 
                        f"funcion_judicial_{_slug(apellidos_nombres)}_resultados_page2"
                    )
                    screenshots_paths.append(screenshot_2)
                    log(f"📸 Screenshot página 2 guardado: {screenshot_2}")
                    
                except Exception as e:
                    log(f"⚠️ Error navegando a página 2: {e}")

        # 10. Resultado final
        resultado = {
            "screenshot_path": screenshots_paths[0] if screenshots_paths else None,
        }

        if len(screenshots_paths) > 1:
            resultado["screenshot_historial_path"] = screenshots_paths[1]
            log(f"✅ Agregando segundo screenshot: {screenshots_paths[1]}")

        return resultado

    except Exception as e:
        log(f"❌ Error en proceso Función Judicial: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

def capture_results_section(driver, basename: str):
    """Captura específicamente la sección de resultados con scroll más profundo"""
    try:
        results_selector = "body > app-root > app-expel-listado-juicios > expel-sidenav > mat-sidenav-container > mat-sidenav-content > section > section"
        
        results_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, results_selector))
        )
        
        if results_container:
            log(f"✅ Encontrado contenedor de resultados")
            
            # PASO 1: Ir al tope
            driver.execute_script("window.scrollTo(0, 0);")
            _wait(driver, 1.0)
            
            # PASO 2: Scroll EXTRA profundo hacia abajo
            log("📜 Scroll EXTRA profundo hacia abajo...")
            driver.execute_script("""
                const totalHeight = Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight
                );
                
                // Scroll MÁS PROFUNDO - agregar píxeles extra
                window.scrollTo(0, totalHeight + 200);  // +200px extra
            """)
            _wait(driver, 2.0)
            
            # PASO 3: Scroll adicional por si acaso
            driver.execute_script("window.scrollBy(0, 150);")  # 150px más
            _wait(driver, 1.0)
            
            # PASO 4: Volver arriba
            log("📜 Regresando hacia arriba...")
            driver.execute_script("window.scrollTo(0, 0);")
            _wait(driver, 1.0)
            
            # PASO 5: Posicionar elemento y ajuste fino
            driver.execute_script("""
                const element = arguments[0];
                element.scrollIntoView({block: 'start', behavior: 'auto'});
                
                // Ajuste más pequeño hacia arriba
                window.scrollBy(0, -50);  // Solo -50px en lugar de -100px
                
                element.scrollTop = 0;
            """, results_container)
            
            _wait(driver, 2.0)
            
            screenshot_path = save_element_screenshot_png(
                driver,
                results_container,
                basename=basename
            )
            
            log(f"📸 Screenshot del contenedor: {screenshot_path}")
            return screenshot_path
            
    except Exception as e:
        log(f"⚠️ Error: {e}")
        return save_fullpage_png(driver, basename=basename + "_fallback")
    
def process_funcion_judicial(apellidos_nombres: str, headless: bool = False) -> Optional[Dict]:
    """
    Ejecuta consulta en Función Judicial con reintentos (SIN caché).
    Sigue el patrón estándar process_[página] usado en el proyecto.
    """
    if not apellidos_nombres or len(apellidos_nombres.strip()) < 3:
        return {"error": "Función Judicial: Ingresa apellidos y nombres válidos"}

    apellidos_nombres = apellidos_nombres.strip()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"--- Procesando FUNCIÓN JUDICIAL '{apellidos_nombres}' (intento {attempt}/{MAX_RETRIES}) ---")
            data = process_funcion_judicial_once(apellidos_nombres, headless=headless)
            if data:
                return data
        except Exception as e:
            log(f"❌ Función Judicial: Error en intento {attempt}: {e}")

        if attempt < MAX_RETRIES:
            wait_time = min(3 + attempt * 2, 10)
            log(f"⏳ Esperando {wait_time}s antes del siguiente intento...")
            time.sleep(wait_time)

    log(f"🛑 Función Judicial: falló el procesamiento para '{apellidos_nombres}' tras {MAX_RETRIES} intentos")
    return {"error": f"No se pudo procesar la consulta tras {MAX_RETRIES} intentos"}

def wait_for_all_results_loaded(driver, timeout: int = 20):
    """Espera a que se carguen todos los resultados de la página actual con múltiples estrategias"""
    try:
        import time
        start_time = time.time()
        last_count = 0
        stable_count = 0
        
        log("🔄 Estrategia 1: Esperando carga estable de resultados...")
        
        while time.time() - start_time < timeout:
            try:
                # Contar filas de la tabla con múltiples selectores
                selectors_to_try = [
                    "table tbody tr",
                    "mat-row",
                    ".mat-mdc-row",
                    "tr[role='row']"
                ]
                
                current_count = 0
                for selector in selectors_to_try:
                    rows = driver.find_elements(By.CSS_SELECTOR, selector)
                    visible_rows = [r for r in rows if r.is_displayed()]
                    if len(visible_rows) > current_count:
                        current_count = len(visible_rows)
                
                log(f"🔢 Resultados detectados: {current_count}")
                
                # Si es estable por 3 segundos consecutivos
                if current_count == last_count and current_count > 0:
                    stable_count += 1
                    if stable_count >= 3:
                        log(f"✅ Carga estable detectada: {current_count} resultados")
                        
                        # Estrategia 2: Verificar que coincida con el paginador
                        try:
                            body_text = driver.execute_script("return document.body.innerText || ''").lower()
                            
                            # Buscar "items por página: 10" y verificar que tenemos 10 o menos
                            if "items por página: 10" in body_text:
                                if current_count == 10:
                                    log("✅ Página completa: 10/10 resultados cargados")
                                    return True
                                elif current_count < 10:
                                    # Verificar si es la última página
                                    if "página 2 de 2" in body_text or "página 1 de 1" in body_text:
                                        log(f"✅ Última página: {current_count} resultados (menos de 10 es normal)")
                                        return True
                                    else:
                                        log(f"⚠️ Solo {current_count}/10 resultados, esperando más...")
                                        stable_count = 0  # Reset y continuar esperando
                            
                        except Exception as e:
                            log(f"⚠️ Error verificando paginador: {e}")
                        
                        # Si llegamos aquí y tenemos resultados estables, aceptar
                        if current_count >= 7:  # Mínimo razonable
                            return True
                else:
                    stable_count = 0
                    
                last_count = current_count
                time.sleep(1)
                
            except Exception as e:
                log(f"⚠️ Error contando resultados: {e}")
                time.sleep(1)
        
        log(f"⏳ Timeout esperando carga completa, procediendo con {last_count} resultados")
        return False
        
    except Exception as e:
        log(f"❌ Error en wait_for_all_results_loaded: {e}")
        return False
# Función de prueba independiente (para testing)
if __name__ == "__main__":
    print("=== PRUEBA FUNCIÓN JUDICIAL ===")
    nombre_prueba = "Vela Vasco Marco Antonio"
    resultado = process_funcion_judicial(nombre_prueba, headless=False)
    print(f"Resultado: {resultado}")