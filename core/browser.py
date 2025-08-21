
# core/browser.py
import subprocess
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from .config import PAGE_LOAD_TIMEOUT

def create_driver(headless=False):
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")                 # reduce errores GL en Windows
    options.add_argument("--log-level=3")                 # 0=ALL, 1=INFO, 2=WARNING, 3=ERROR
    # Quita logs verbosos del propio Chrome
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option('useAutomationExtension', False)

    # Silenciar salida del ChromeDriver
    service = Service(
        ChromeDriverManager().install(),
        log_output=subprocess.DEVNULL
    )

    driver = Chrome(service=service, options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver
