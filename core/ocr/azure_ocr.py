# core/ocr/azure_ocr.py
import os, base64, re, time
from typing import Optional

import httpx
from openai import AzureOpenAI
from openai import APIStatusError, OpenAIError

from core.utils.log import log

# === ENV ===
AZ_ENDPOINT = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
AZ_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
# Compat: permitimos API_VERSION (tu .env) y fallback a AZURE_OPENAI_API_VERSION
AZ_API_VERSION = os.getenv("API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
AZ_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
AZ_DEBUG = os.getenv("AZURE_OCR_DEBUG", "0") == "1"

# httpx como en tu snippet (nota: verify=False desactiva validación TLS; úsalo con cuidado)
_httpx = httpx.Client(timeout=30.0, verify=False, proxies=None)

_client: Optional[AzureOpenAI] = None

def _get_client() -> Optional[AzureOpenAI]:
    global _client
    if _client:
        return _client
    if not (AZ_ENDPOINT and AZ_API_KEY and AZ_API_VERSION):
        log("⚠️ Azure OpenAI: faltan variables .env (AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / API_VERSION).")
        return None
    try:
        _client = AzureOpenAI(
            api_key=AZ_API_KEY,
            api_version=AZ_API_VERSION,
            azure_endpoint=AZ_ENDPOINT,
            http_client=_httpx,
        )
        log("✅ Azure OpenAI client initialized successfully")
        return _client
    except Exception as e:
        log(f"❌ Error initializing Azure OpenAI client: {e}")
        return None

def _img_to_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    # El captcha que guardamos es PNG; si tienes JPG ajusta el mime.
    return f"data:image/png;base64,{b64}"

def _sanitize_alnum(s: str) -> str:
    # Captchas alfanuméricos, longitud variable
    s = (s or "").strip().upper()
    return re.sub(r"[^A-Z0-9]", "", s)

def _explain_404():
    log("💡 Pista 404 DeploymentNotFound:")
    log("   - AZURE_OPENAI_DEPLOYMENT debe coincidir EXACTO con el *nombre del deployment* en Azure (no el nombre del modelo).")
    log("   - El deployment debe soportar visión (p.ej. gpt-4o-mini).")
    log("   - Revisa .env: AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / AZURE_OPENAI_DEPLOYMENT / API_VERSION")

def solve_captcha_with_azure(image_path: str, attempts: int = 2, temperature: float = 0.0) -> Optional[str]:
    """
    Envía la imagen al deployment (chat completions multimodal) y devuelve el texto del captcha (A-Z0-9).
    Retorna None si no se pudo leer.
    """
    if not AZ_DEPLOYMENT:
        log("⚠️ Azure OCR: falta AZURE_OPENAI_DEPLOYMENT en .env")
        return None

    client = _get_client()
    if not client:
        return None

    data_uri = _img_to_data_uri(image_path)
    system_message = (
        "Eres un OCR de captchas. Devuelve exclusivamente el texto que aparece en la imagen. "
        "Sin explicaciones, ni comillas, ni espacios adicionales. "
        "Respeta el orden. Si hay letras, devuélvelas en MAYÚSCULAS."
    )
    user_content = [
        {"type": "text", "text": "Lee este captcha y responde SOLO la cadena exacta (sin espacios):"},
        {"type": "image_url", "image_url": {"url": data_uri}},
    ]

    log(f"[OCR] Endpoint='{AZ_ENDPOINT}'  Deployment='{AZ_DEPLOYMENT}'  Version='{AZ_API_VERSION}'")
    for i in range(1, attempts + 1):
        try:
            log(f"[OCR] Intento {i}/{attempts} → chat.completions.create(model={AZ_DEPLOYMENT})")
            resp = client.chat.completions.create(
                model=AZ_DEPLOYMENT,  # IMPORTANTE: aquí va el NOMBRE DEL DEPLOYMENT
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                top_p=0.0,
                max_tokens=24,
            )
            raw = (resp.choices[0].message.content or "").strip()
            if AZ_DEBUG:
                log(f"[OCR] Respuesta bruta: {raw!r}")
            clean = _sanitize_alnum(raw)
            if clean:
                log(f"[OCR] Texto detectado (len={len(clean)}): {clean}")
                return clean
            else:
                log("[OCR] Respuesta vacía/invalidada tras sanitizar.")
                time.sleep(0.6)

        except APIStatusError as e:
            # Errores HTTP de la API (4xx/5xx)
            status = getattr(e, "status_code", None)
            body = getattr(e, "response", None)
            body_txt = ""
            try:
                body_txt = body.text[:400].replace("\n", " ") if body else str(e)[:400]
            except Exception:
                body_txt = str(e)[:400]
            log(f"❌ Azure OCR HTTP {status}: {body_txt}")
            if status == 404 and ("DeploymentNotFound" in body_txt or "deployment" in body_txt.lower()):
                _explain_404()
            time.sleep(0.8)

        except OpenAIError as e:
            # Otros errores del SDK
            log(f"❌ Azure OCR (OpenAIError): {e}")
            time.sleep(0.8)

        except Exception as e:
            log(f"❌ Azure OCR (Exception): {e}")
            time.sleep(0.8)

    log("❌ OCR: no se pudo leer el captcha.")
    return None
