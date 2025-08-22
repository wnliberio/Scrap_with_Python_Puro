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

