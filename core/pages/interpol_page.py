# core/pages/interpol_page.py
import time
import random
from typing import Optional, List

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
)

INTERPOL_URL = "https://www.interpol.int/es/Como-trabajamos/Notificaciones/Notificaciones-rojas/Ver-las-notificaciones-rojas"

# -----------------------------
# Finders de elementos del form
# -----------------------------
def _wait(driver, secs: float):
    time.sleep(random.uniform(secs * 0.6, secs * 1.1))

def find_surname_input(driver, timeout: int = 20):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "name"))
        )
    except TimeoutException:
        return None

def find_forename_input(driver, timeout: int = 10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "forename"))
        )
    except TimeoutException:
        return None

def find_submit_button(driver, timeout: int = 10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "submit"))
        )
    except TimeoutException:
        return None

# --------------------------------
# FUNCIONES ACTUALIZADAS: Detectar y obtener elementos específicos para captura
# --------------------------------
def find_detail_panel(driver, timeout: int = 10):
    """
    Encuentra el panel completo #singlePanel (no el div hijo)
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "singlePanel"))
        )
    except TimeoutException:
        return None

def find_no_results_section(driver, timeout: int = 10):
    """
    Encuentra la sección de "no hay resultados" usando XPath
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='listPanel']/div[6]/div"))
        )
    except TimeoutException:
        # Fallback: buscar por texto "No hay resultados"
        try:
            return WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'No hay resultados')]//ancestor::div[1]"))
            )
        except TimeoutException:
            # Otro fallback: buscar el contenedor de resultados vacío
            try:
                return WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#noticesResults"))
                )
            except TimeoutException:
                return None

def detect_search_result_state(driver, timeout: int = 35) -> str:
    """
    Detecta el estado después de hacer la búsqueda.
    Retorna:
      - 'results_found' -> hay lista de resultados
      - 'no_results'    -> página sin resultados/en blanco
      - 'timeout'       -> no se pudo determinar
    """
    end = time.time() + timeout
    
    while time.time() < end:
        try:
            # Verificar si hay lista de resultados
            container = driver.find_elements(By.ID, "noticesResultsItemList")
            if container:
                # Verificar si tiene elementos dentro
                anchors = container[0].find_elements(By.CSS_SELECTOR, "a.redNoticeItem__labelLink")
                if anchors:
                    _wait(driver, 0.5)
                    return "results_found"
            
            # Verificar mensaje de "no resultados" en el texto de la página
            body_text = (driver.execute_script("return document.body.innerText || ''") or "").lower()
            no_results_indicators = [
                "no hay resultados para su búsqueda",
                "no hay resultados",
                "no se encontraron",
                "sin resultados",
                "no results",
                "no se han encontrado",
                "seleccione otros criterios"
            ]
            
            if any(indicator in body_text for indicator in no_results_indicators):
                return "no_results"
            
            # Verificar si existe el elemento específico de "no resultados"
            no_results_element = find_no_results_section(driver, timeout=2)
            if no_results_element and no_results_element.is_displayed():
                return "no_results"
            
            # Verificar si la página está "vacía" (contenido mínimo después de búsqueda)
            # Si han pasado más de 10 segundos y no hay contenedor de resultados ni mensaje
            if time.time() - (end - timeout) > 10 and not container:
                content_length = len(body_text.strip())
                # Si el contenido es muy poco, probablemente no hay resultados
                if content_length < 1000:  # ajustar según observación
                    return "no_results"
            
            time.sleep(0.5)
            
        except Exception as e:
            time.sleep(0.5)
    
    return "timeout"

# --------------------------------
# Resultados de la lista (paginada) - MANTENER FUNCIONES EXISTENTES
# --------------------------------
def wait_results_list(driver, timeout: int = 35) -> bool:
    """
    Espera a que aparezca la lista de resultados.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "noticesResultsItemList"))
        )
        # En algunos casos tarda en hidratar los <a>, esperamos al menos uno.
        WebDriverWait(driver, max(8, timeout // 3)).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.redNoticeItem__labelLink"))
        )
        _wait(driver, 0.5)
        return True
    except TimeoutException:
        return False

def _collect_result_anchors(driver) -> List:
    try:
        container = driver.find_element(By.ID, "noticesResultsItemList")
        return container.find_elements(By.CSS_SELECTOR, "a.redNoticeItem__labelLink")
    except Exception:
        return []

def _normalize(s: str) -> str:
    return " ".join((s or "").split()).upper()

def _score_match(text: str, query: str) -> int:
    """
    Suma puntos por cada token del query que aparezca en text.
    """
    t = _normalize(text)
    q = [tok for tok in _normalize(query).split() if tok]
    return sum(1 for tok in q if tok in t)

def _best_anchor_index_by_score(driver, wanted_text: str) -> Optional[int]:
    anchors = _collect_result_anchors(driver)
    if not anchors:
        return None
    best_idx = None
    best_score = -1
    for i, a in enumerate(anchors, start=1):
        try:
            txt = a.text or ""
        except StaleElementReferenceException:
            continue
        score = _score_match(txt, wanted_text)
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx

def _get_anchor_by_index(driver, index: int):
    anchors = _collect_result_anchors(driver)
    if 1 <= index <= len(anchors):
        return anchors[index - 1]
    return None

def hover_and_click_name(driver, index: int) -> bool:
    """
    Hace hover y clic *sobre el texto del nombre* (anchor).
    Rebusca el elemento si se vuelve stale.
    """
    try:
        anchor = _get_anchor_by_index(driver, index)
        if not anchor:
            return False

        # Posicionar el scroll y el cursor sobre el texto
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", anchor)
        _wait(driver, 0.25)

        try:
            ActionChains(driver).move_to_element(anchor).pause(0.25).click().perform()
        except StaleElementReferenceException:
            # Reubicar y reintentar una vez
            anchor = _get_anchor_by_index(driver, index)
            if not anchor:
                return False
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", anchor)
            _wait(driver, 0.2)
            ActionChains(driver).move_to_element(anchor).pause(0.25).click().perform()

        return True
    except Exception:
        return False

def _pick_anchor_index_by_text(driver, wanted_text: str) -> Optional[int]:
    """
    Devuelve el índice (1-based) del <a> con mejor score respecto a `wanted_text`.
    """
    return _best_anchor_index_by_score(driver, wanted_text)

# -------------------------
# Detalle (panel individual)
# -------------------------
def wait_detail_panel(driver, timeout: int = 40) -> bool:
    """
    Espera a que se renderice el panel individual, incluyendo la columna derecha
    `.wantedsingle__colright` para asegurar que la info principal esté cargada.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "singlePanel"))
        )
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".wantedsingle, #singlePanel"))
        )
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".wantedsingle__colright"))
        )
        # Pequeño settle para estilos/imagenes
        _wait(driver, 0.9)
        return True
    except TimeoutException:
        return False