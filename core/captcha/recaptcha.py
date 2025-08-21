# core/captcha/recaptcha.py
import time, base64, random
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from ..config import (
    CAPSOLVER_API_KEY,
    CAPSOLVER_URL,
    CAPSOLVER_RESULT_URL,
    RECAPTCHA_TIMEOUT,
)
from ..utils.log import log

def capture_recaptcha_challenge(driver):
    """
    Captura la imagen completa de la cuadrícula y extrae la pregunta.
    Retorna: ([image_base64], question_text). No guarda archivos.
    """
    try:
        driver.switch_to.default_content()
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
        )
        driver.switch_to.frame(iframe)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".rc-imageselect-target"))
        )

        question_element = driver.find_element(By.CSS_SELECTOR, ".rc-imageselect-desc-no-canonical")
        question_text = question_element.text.strip()
        log(f"[CAPTCHA] Pregunta extraída: {question_text}")

        table_element = driver.find_element(By.CSS_SELECTOR, ".rc-imageselect-table-33")
        screenshot = table_element.screenshot_as_png
        image_base64 = base64.b64encode(screenshot).decode("utf-8")

        driver.switch_to.default_content()
        return [image_base64], question_text

    except Exception as e:
        log(f"[CAPTCHA] ❌ Error capturando desafío: {e}")
        driver.switch_to.default_content()
        return None, None

def solve_with_capsolver(images_base64_list, question):
    """
    Envía la imagen a CapSolver y retorna coordenadas para hacer clic.
    """
    try:
        log("[CAPTCHA] 🚀 Enviando imagen completa a CapSolver...")
        if not images_base64_list:
            log("[CAPTCHA] ❌ Lista de imágenes vacía")
            return None

        complete_image_base64 = images_base64_list[0]
        task_data = {
            "clientKey": CAPSOLVER_API_KEY,
            "task": {
                "type": "ReCaptchaV2Classification",
                "imageBody": complete_image_base64,
                "question": question
            }
        }

        response = requests.post(CAPSOLVER_URL, json=task_data, timeout=30)
        result = response.json()

        if result.get("errorId") != 0:
            log(f"[CAPTCHA] ❌ Error creando tarea: {result.get('errorDescription')}")
            return None

        task_id = result.get("taskId")
        log(f"[CAPTCHA] 📝 Tarea creada: {task_id}")

        # Polling resultado
        for attempt in range(30):
            time.sleep(2)
            result_data = {"clientKey": CAPSOLVER_API_KEY, "taskId": task_id}
            response = requests.post(CAPSOLVER_RESULT_URL, json=result_data, timeout=30)
            result = response.json()

            if result.get("status") == "ready":
                sol = result.get("solution", {})
                if "coordinates" in sol:
                    coords = sol["coordinates"]
                    log(f"[CAPTCHA] ✅ Coordenadas: {coords}")
                    return coords
                log(f"[CAPTCHA] ❌ Formato de solución desconocido: {sol}")
                return None
            elif result.get("status") == "processing":
                log(f"[CAPTCHA] ⏳ Procesando... (intento {attempt+1}/30)")
            else:
                log(f"[CAPTCHA] ❌ Error en resultado: {result}")
                return None

        log("[CAPTCHA] ❌ Timeout esperando resultado de CapSolver")
        return None

    except Exception as e:
        log(f"[CAPTCHA] ❌ Error con CapSolver: {e}")
        return None

def click_recaptcha_coordinates(driver, coordinates):
    """
    Hace clic en las coordenadas devueltas por CapSolver dentro del iframe.
    """
    try:
        driver.switch_to.default_content()
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
        )
        driver.switch_to.frame(iframe)

        table_element = driver.find_element(By.CSS_SELECTOR, ".rc-imageselect-table-33")
        log(f"[CAPTCHA] 🖱️ Clic en {len(coordinates)} coordenadas...")

        for i, (x, y) in enumerate(coordinates):
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(driver)
                actions.move_to_element_with_offset(table_element, x, y)
                actions.pause(random.uniform(0.1, 0.3))
                actions.click()
                actions.perform()
                log(f"[CAPTCHA] ✅ Clic {i+1} en ({x}, {y})")
                time.sleep(random.uniform(0.2, 0.5))
            except Exception as e:
                log(f"[CAPTCHA] ❌ Error clic ({x}, {y}): {e}")

        driver.switch_to.default_content()
        return True

    except Exception as e:
        log(f"[CAPTCHA] ❌ Error haciendo clics: {e}")
        driver.switch_to.default_content()
        return False

def click_verify_button(driver):
    """
    Hace clic en el botón 'Verificar' del desafío.
    """
    try:
        driver.switch_to.default_content()
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
        )
        driver.switch_to.frame(iframe)

        verify_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#recaptcha-verify-button"))
        )

        from selenium.webdriver.common.action_chains import ActionChains
        actions = ActionChains(driver)
        actions.move_to_element(verify_button)
        actions.pause(random.uniform(0.1, 0.3))
        actions.click()
        actions.perform()

        log("[CAPTCHA] ✅ Botón Verificar presionado")
        driver.switch_to.default_content()
        time.sleep(2)
        return True

    except Exception as e:
        log(f"[CAPTCHA] ❌ Error clic Verificar: {e}")
        driver.switch_to.default_content()
        return False

def solve_recaptcha_automatically(driver):
    """
    Orquesta la resolución automática con CapSolver.
    """
    try:
        log("[CAPTCHA] 🤖 Iniciando resolución automática...")
        images_base64_list, question = capture_recaptcha_challenge(driver)
        if not images_base64_list or not question:
            log("[CAPTCHA] ❌ No se pudieron capturar imágenes o pregunta")
            return False

        coordinates = solve_with_capsolver(images_base64_list, question)
        if not coordinates:
            log("[CAPTCHA] ❌ CapSolver no devolvió coordenadas")
            return False

        if not click_recaptcha_coordinates(driver, coordinates):
            log("[CAPTCHA] ❌ Error clic en coordenadas")
            return False

        if not click_verify_button(driver):
            log("[CAPTCHA] ❌ Error clic en Verificar")
            return False

        time.sleep(3)
        try:
            token = driver.execute_script(
                "return (window.grecaptcha && grecaptcha.getResponse) ? grecaptcha.getResponse() : ''"
            )
            if token:
                log("[CAPTCHA] ✅ reCAPTCHA resuelto automáticamente!")
                return True
            else:
                log("[CAPTCHA] ⚠️ Token no encontrado post-resolución")
                return False
        except Exception as e:
            log(f"[CAPTCHA] ⚠️ Error verificando token: {e}")
            return False

    except Exception as e:
        log(f"[CAPTCHA] ❌ Error en resolución automática: {e}")
        return False

def wait_for_recaptcha_solved(driver, timeout=RECAPTCHA_TIMEOUT):
    """
    Intenta resolver automáticamente; si falla, espera resolución manual (HITL) hasta timeout.
    """
    start = time.time()
    try:
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
        if not any(f.is_displayed() for f in iframes):
            log("[CAPTCHA] 👍 No hay reCAPTCHA presente")
            return True

        try:
            token = driver.execute_script(
                "return (window.grecaptcha && grecaptcha.getResponse) ? grecaptcha.getResponse() : ''"
            )
            if token:
                log("[CAPTCHA] ✅ reCAPTCHA ya resuelto")
                return True
        except Exception:
            pass

        log("[CAPTCHA] 🔍 reCAPTCHA detectado, resolviendo...")
        auto_start = time.time()
        if solve_recaptcha_automatically(driver):
            log(f"[CAPTCHA] ✅ Resuelto automáticamente en {time.time()-start:.1f}s")
            return True

        log(f"[CAPTCHA] ⚠️ Auto falló en {time.time()-auto_start:.1f}s. Esperando resolución manual…")
        log("🟡 Por favor resuelve el CAPTCHA manualmente en el navegador…")

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
                    val = (ta.get_attribute("value") or "").strip()
                    if val:
                        return True
            except Exception:
                pass
            return False

        manual_timeout = max(120, timeout - (time.time() - auto_start))
        WebDriverWait(driver, manual_timeout, poll_frequency=0.5).until(lambda d: token_present(d))

        log(f"🟢 CAPTCHA resuelto manualmente (total {time.time()-start:.1f}s). Continuando…")
        try:
            driver.execute_script("document.body.style.zoom='1'")
        except Exception:
            pass
        return True

    except TimeoutException:
        log(f"[CAPTCHA] ❌ Timeout tras {time.time()-start:.1f}s sin resolver el CAPTCHA")
        return False
    except Exception as e:
        log(f"[CAPTCHA] ❌ Error manejando reCAPTCHA: {e}")
        return False
