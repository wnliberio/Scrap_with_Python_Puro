# core/browser.py
"""
Creación de WebDriver con anti-detección y anti-captcha mejorados.
Estrategias implementadas:
- User agents rotativos actualizados
- Fingerprinting reducido
- Tamaños de ventana variables
- Configuración regional (Ecuador)
- Cookies persistentes
- Headers HTTP realistas
"""

import os
import random
import pickle
from pathlib import Path
from typing import Optional

try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    UNDETECTED_AVAILABLE = False

from core.utils.log import log


# Directorio para cookies persistentes
COOKIES_DIR = Path("sri_ruc_output/cookies")
COOKIES_DIR.mkdir(parents=True, exist_ok=True)


# User Agents actualizados (2025)
USER_AGENTS = [
    # Chrome en Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    
    # Chrome en macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    
    # Edge (basado en Chromium)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
]


# Tamaños de ventana realistas (ancho, alto)
WINDOW_SIZES = [
    (1366, 768),   # Laptop común
    (1440, 900),   # MacBook
    (1536, 864),   # Laptop HD+
    (1920, 1080),  # Desktop Full HD
    (1680, 1050),  # Desktop 16:10
]


def _get_random_user_agent() -> str:
    """Retorna user agent aleatorio de la lista"""
    return random.choice(USER_AGENTS)


def _get_random_window_size() -> tuple:
    """Retorna tamaño de ventana aleatorio"""
    return random.choice(WINDOW_SIZES)


def save_cookies(driver, domain: str = "funcionjudicial"):
    """
    Guarda cookies del driver actual para reutilizar en futuras sesiones.
    
    Args:
        driver: WebDriver de Selenium
        domain: Nombre del dominio (para identificar el archivo)
    """
    try:
        cookie_file = COOKIES_DIR / f"{domain}_cookies.pkl"
        cookies = driver.get_cookies()
        
        with open(cookie_file, 'wb') as f:
            pickle.dump(cookies, f)
        
        log(f"Cookies guardadas: {cookie_file}")
    except Exception as e:
        log(f"Error guardando cookies: {e}")


def load_cookies(driver, domain: str = "funcionjudicial"):
    """
    Carga cookies guardadas previamente.
    
    Args:
        driver: WebDriver de Selenium
        domain: Nombre del dominio
    
    Returns:
        bool: True si se cargaron cookies, False si no
    """
    try:
        cookie_file = COOKIES_DIR / f"{domain}_cookies.pkl"
        
        if not cookie_file.exists():
            log("No hay cookies guardadas para cargar")
            return False
        
        with open(cookie_file, 'rb') as f:
            cookies = pickle.load(f)
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                # Algunas cookies pueden fallar (por dominio, expiración, etc)
                continue
        
        log(f"Cookies cargadas: {len(cookies)} cookies desde {cookie_file}")
        return True
        
    except Exception as e:
        log(f"Error cargando cookies: {e}")
        return False


def _apply_stealth_js(driver):
    """
    Aplica JavaScript para ocultar señales de automatización.
    Solo para Selenium normal (undetected-chromedriver ya lo hace).
    """
    stealth_scripts = [
        # Ocultar navigator.webdriver
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """,
        
        # Sobrescribir permisos
        """
        Object.defineProperty(navigator, 'permissions', {
            get: () => ({
                query: () => Promise.resolve({ state: 'granted' })
            })
        });
        """,
        
        # Plugins falsos
        """
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        """,
        
        # Languages
        """
        Object.defineProperty(navigator, 'languages', {
            get: () => ['es-EC', 'es', 'en-US', 'en']
        });
        """,
        
        # Chrome runtime
        """
        window.chrome = {
            runtime: {}
        };
        """,
        
        # Hardware concurrency (cores del CPU)
        """
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8
        });
        """,
        
        # Device memory
        """
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
        });
        """,
    ]
    
    for script in stealth_scripts:
        try:
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': script
            })
        except Exception:
            pass


def create_driver(headless: bool = False, use_cookies: bool = True, cookies_domain: str = "funcionjudicial") -> 'WebDriver':
    """
    Crea WebDriver con anti-detección y anti-captcha mejorados.
    
    Args:
        headless: Si True, ejecuta en modo headless
        use_cookies: Si True, intenta cargar cookies guardadas
        cookies_domain: Dominio para las cookies
    
    Returns:
        WebDriver configurado
    """
    user_agent = _get_random_user_agent()
    width, height = _get_random_window_size()
    
    log(f"Creando driver (headless={headless})")
    log(f"User Agent: {user_agent[:60]}...")
    log(f"Tamaño ventana: {width}x{height}")
    
    if UNDETECTED_AVAILABLE:
        # ===== UNDETECTED-CHROMEDRIVER (Recomendado) =====
        log("Usando undetected-chromedriver (anti-detección automática)")
        
        options = uc.ChromeOptions()
        
        # Headless
        if headless:
            options.add_argument('--headless=new')
        
        # Configuración básica
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument(f'--window-size={width},{height}')
        
        # User agent personalizado
        options.add_argument(f'--user-agent={user_agent}')
        
        # Idioma (Ecuador)
        options.add_argument('--lang=es-EC,es')
        options.add_argument('--accept-lang=es-EC,es;q=0.9,en;q=0.8')
        
        # Deshabilitar funciones de automatización
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Preferencias adicionales
        prefs = {
            "profile.default_content_setting_values.notifications": 2,  # Bloquear notificaciones
            "profile.managed_default_content_settings.images": 1,  # Permitir imágenes
            "intl.accept_languages": "es-EC,es,en-US,en",
        }
        options.add_experimental_option("prefs", prefs)
        
        # Crear driver
        try:
            driver = uc.Chrome(
                options=options,
                version_main=140,  # Versión más reciente de Chrome
                driver_executable_path=None,
                browser_executable_path=None,
            )
        except Exception as e:
            log(f"Error con version_main=140, intentando sin especificar versión: {e}")
            driver = uc.Chrome(options=options)
        
        # Configurar headers HTTP adicionales vía CDP
        try:
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent,
                "acceptLanguage": "es-EC,es;q=0.9,en;q=0.8",
                "platform": "Win32"
            })
        except Exception as e:
            log(f"No se pudo configurar Network override: {e}")
        
        # Cargar cookies si existen
        if use_cookies:
            # Primero navegar al dominio para poder setear cookies
            try:
                driver.get("https://procesosjudiciales.funcionjudicial.gob.ec")
                load_cookies(driver, domain=cookies_domain)
            except Exception as e:
                log(f"Error cargando cookies: {e}")
        
        log("Driver undetected creado exitosamente")
        
    else:
        # ===== SELENIUM NORMAL CON ANTI-DETECCIÓN MANUAL =====
        log("Usando Selenium normal con anti-detección manual")
        
        options = Options()
        
        # Configuración headless
        if headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument(f'--window-size={width},{height}')
        
        # User agent
        options.add_argument(f'--user-agent={user_agent}')
        
        # Idioma
        options.add_argument('--lang=es-EC,es')
        
        # Deshabilitar automatización detectada
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Preferencias
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "intl.accept_languages": "es-EC,es,en-US,en",
        }
        options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=options)
        
        # Aplicar scripts anti-detección
        _apply_stealth_js(driver)
        
        # Configurar headers adicionales
        try:
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent,
                "acceptLanguage": "es-EC,es;q=0.9,en;q=0.8",
                "platform": "Win32"
            })
        except Exception:
            pass
        
        # Cargar cookies
        if use_cookies:
            try:
                driver.get("https://procesosjudiciales.funcionjudicial.gob.ec")
                load_cookies(driver, domain=cookies_domain)
            except Exception as e:
                log(f"Error cargando cookies: {e}")
        
        log("Driver Selenium creado con anti-detección manual")
    
    return driver


def close_driver(driver, save_cookies_flag: bool = True, cookies_domain: str = "funcionjudicial"):
    """
    Cierra el driver guardando cookies si se especifica.
    
    Args:
        driver: WebDriver a cerrar
        save_cookies_flag: Si True, guarda cookies antes de cerrar
        cookies_domain: Dominio para guardar cookies
    """
    try:
        if save_cookies_flag:
            save_cookies(driver, domain=cookies_domain)
    except Exception as e:
        log(f"Error guardando cookies al cerrar: {e}")
    
    try:
        driver.quit()
        log("Driver cerrado exitosamente")
    except Exception as e:
        log(f"Error cerrando driver: {e}")