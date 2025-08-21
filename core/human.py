import math, random, time
import pyautogui
from .config import (
    TYPE_BASE_DELAY, TYPE_JITTER, TYPE_PUNCT_PAUSE,
    MOUSE_MIN_TIME, MOUSE_MAX_TIME, MOUSE_STEPS, MOUSE_JITTER
)

def human_type(element, text, base_delay=TYPE_BASE_DELAY, jitter=TYPE_JITTER, punctuation_pause=TYPE_PUNCT_PAUSE):
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

def _ease_in_out_quad(t: float) -> float:
    return 2*t*t if t < 0.5 else -1 + (4 - 2*t)*t

def _bezier_cubic(p0, p1, p2, p3, t):
    x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
    y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
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
        time.sleep(max(0.0, target_time - elapsed))

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
