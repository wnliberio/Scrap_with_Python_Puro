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
# Resultados de la lista (paginada)
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
