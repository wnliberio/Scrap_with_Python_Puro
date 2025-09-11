import os, base64
from datetime import datetime
from ..config import SCREENSHOT_DIR

def save_fullpage_png(driver, basename: str) -> str:
    """
    Captura una imagen PNG de página completa usando CDP (Chrome).
    Retorna la RUTA ABSOLUTA del archivo guardado.
    """
    try:
        driver.execute_cdp_cmd("Page.enable", {})
    except Exception:
        pass

    metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
    content = metrics.get("contentSize") or metrics.get("cssContentSize") or {}
    width  = float(content.get("width", 0)) or 1920.0
    height = float(content.get("height", 0)) or 3000.0

    result = driver.execute_cdp_cmd("Page.captureScreenshot", {
        "format": "png",
        "captureBeyondViewport": True,
        "fromSurface": True,
        "clip": { "x": 0, "y": 0, "width": width, "height": height, "scale": 1 }
    })

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{basename}_{ts}.png"
    outpath = os.path.join(SCREENSHOT_DIR, filename)

    with open(outpath, "wb") as f:
        f.write(base64.b64decode(result["data"]))

    return os.path.abspath(outpath)


def save_element_full_screenshot_cdp(driver, element, basename: str) -> str:
    """
    Captura un elemento completo usando CDP, incluso si es más grande que el viewport.
    Retorna la RUTA ABSOLUTA del archivo guardado.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{basename}_{ts}.png"
    outpath = os.path.join(SCREENSHOT_DIR, filename)
    
    try:
        # Habilitar CDP
        driver.execute_cdp_cmd("Page.enable", {})
        
        # Obtener las coordenadas y dimensiones del elemento
        location = element.location
        size = element.size
        
        # Asegurar que las dimensiones sean válidas
        x = float(location['x'])
        y = float(location['y'])
        width = float(size['width'])
        height = float(size['height'])
        
        if width <= 0 or height <= 0:
            raise Exception(f"Dimensiones inválidas: width={width}, height={height}")
        
        # Capturar usando CDP con las coordenadas exactas del elemento
        result = driver.execute_cdp_cmd("Page.captureScreenshot", {
            "format": "png",
            "captureBeyondViewport": True,
            "fromSurface": True,
            "clip": {
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "scale": 1
            }
        })
        
        # Guardar la imagen
        with open(outpath, "wb") as f:
            f.write(base64.b64decode(result["data"]))
        
        return os.path.abspath(outpath)
        
    except Exception as e:
        print(f"ERROR en captura CDP del elemento: {e}")
        print(f"Ubicación: {element.location}, Tamaño: {element.size}")
        # Fallback a captura completa
        return save_fullpage_png(driver, basename + "_fallback")


def save_element_screenshot_png(driver, element, basename: str) -> str:
    """
    Captura un elemento usando el mejor método disponible.
    Primero intenta CDP para captura completa, luego fallback a método estándar.
    """
    try:
        # Intentar captura completa con CDP
        return save_element_full_screenshot_cdp(driver, element, basename)
    except Exception as e:
        print(f"CDP falló: {e}. Intentando método estándar...")
        
        # Fallback al método estándar de Selenium
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{basename}_{ts}.png"
        outpath = os.path.join(SCREENSHOT_DIR, filename)
        
        try:
            element.screenshot(outpath)
            return os.path.abspath(outpath)
        except Exception as e2:
            print(f"Método estándar también falló: {e2}")
            # Último recurso: captura completa de página
            return save_fullpage_png(driver, basename + "_complete_fallback")


def save_element_by_selector_png(driver, selector: str, basename: str, by_xpath: bool = False) -> str:
    """
    Captura un elemento encontrado por selector CSS o XPath.
    Retorna la RUTA ABSOLUTA del archivo guardado.
    """
    from selenium.webdriver.common.by import By
    
    try:
        if by_xpath:
            element = driver.find_element(By.XPATH, selector)
        else:
            element = driver.find_element(By.CSS_SELECTOR, selector)
        
        return save_element_screenshot_png(driver, element, basename)
        
    except Exception as e:
        print(f"No se pudo capturar elemento '{selector}': {e}")
        return save_fullpage_png(driver, basename + "_fallback")