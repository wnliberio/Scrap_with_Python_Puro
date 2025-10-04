# core/report/report_builder.py
import os, io, json, datetime
from typing import Dict, Any, List, Optional, Tuple

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image

# Opcional: Azure OpenAI (resumen y conclusión)
# Si NO configuras Azure, hacemos fallback a texto heurístico.
AZURE_USE = os.getenv("USE_LLM_ANALYSIS", "0") == "1"
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")  # p.ej. "gpt-4o-mini"

def _safe_dir(path: str):
    os.makedirs(path, exist_ok=True)
    return path

def _fmt_money(v: Optional[float]) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "-"

def _try_llm_analysis(tipo_alerta: str, monto: Optional[float], fecha_alerta: str,
                      items: List[Tuple[str, List[str]]]) -> Tuple[Dict[str, str], str]:
    """
    Devuelve (analisis_por_pagina, conclusion_final).
    Si no hay Azure config, retorna texto heurístico breve.
    items: lista de (tipo, [rutas_de_capturas])
    """
    if not (AZURE_USE and AZURE_ENDPOINT and AZURE_API_KEY and AZURE_DEPLOYMENT):
        # Fallback simple (2 líneas por página, conclusión más amplia)
        por_pagina = {}
        for tipo, paths in items:
            por_pagina[tipo] = (
                "Se adjunta evidencia visual de la consulta realizada. "
                "No se extrajo texto programáticamente; se requiere revisión humana."
            )
        conclusion = (
            "Con base en las páginas revisadas (ver capturas), no se realizó extracción de datos numéricos; "
            "por lo tanto, la corroboración exacta del monto depende de la inspección manual. "
            "Recomendación: verificar si los hallazgos son consistentes con el monto "
            f"{_fmt_money(monto)} de la alerta '{tipo_alerta}' con fecha {fecha_alerta}."
        )
        return por_pagina, conclusion

    # Azure OpenAI (resumen breve y conclusión)
    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version="2024-02-01",
            azure_endpoint=AZURE_ENDPOINT,
        )
        # NO enviamos imágenes; solo contexto de tipos y rutas, para redactado.
        prompt = (
            "Eres un asistente que redacta un informe breve y profesional.\n"
            "Se te dan: tipo de alerta, monto (USD), fecha y las consultas realizadas (por tipo) con capturas.\n"
            "Tareas:\n"
            "1) Para CADA consulta, escribe máx. 2 líneas con un análisis breve (estilo: 'Se observó X / Se requiere verificación manual').\n"
            "2) Escribe una CONCLUSIÓN FINAL (1 párrafo) indicando si, a partir de las consultas, "
            "parece razonable/consistente el monto transaccionado.\n"
            "No inventes datos no visibles. Evita claims numéricos.\n\n"
        )
        payload = {
            "tipo_alerta": tipo_alerta,
            "monto_usd": monto,
            "fecha_alerta": fecha_alerta,
            "consultas": [{"tipo": t, "capturas": p} for t, p in items]
        }
        prompt += f"Datos:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        prompt += "Devuelve JSON con shape {'por_pagina': {tipo: texto}, 'conclusion': texto}."

        resp = client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Asistente de informes concisos y profesionales."},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content
        data = json.loads(content) if content else {}
        por_pagina = data.get("por_pagina", {})
        conclusion = data.get("conclusion", "")
        if not por_pagina or not conclusion:
            raise ValueError("Respuesta LLM vacía o malformada.")
        return por_pagina, conclusion
    except Exception:
        # Fallback si Azure falla
        por_pagina = {}
        for tipo, paths in items:
            por_pagina[tipo] = (
                "Se adjunta evidencia visual de la consulta realizada. "
                "No se extrajo texto programáticamente; se requiere verificación manual."
            )
        conclusion = (
            "Con las evidencias adjuntas, la validación del monto transaccionado requiere revisión humana. "
            f"Monto de alerta: {_fmt_money(monto)}. Tipo: {tipo_alerta}. Fecha: {fecha_alerta}."
        )
        return por_pagina, conclusion


def _insert_image(doc: Document, img_path: str, max_width_in: float = 6.0):
    """
    Inserta imagen reduciendo ancho máximo (mantiene proporción).
    """
    if not (img_path and os.path.exists(img_path)):
        return
    try:
        with Image.open(img_path) as im:
            w, h = im.size
            # ancho max 6 pulgadas aprox (A4 márgenes estándar)
            doc.add_picture(img_path, width=Inches(max_width_in))
    except Exception:
        # Inserción directa si PIL falla igual probar
        try:
            doc.add_picture(img_path, width=Inches(max_width_in))
        except Exception:
            pass


def build_report_docx(
    meta: Dict[str, Any],
    results: Dict[str, Any],
    out_dir: str = os.path.join("sri_ruc_output", "reports"),
) -> Dict[str, Any]:
    """
    Genera un DOCX con estilo sobrio (tipo APA light):
    - Portada breve (tipo alerta, monto, fecha)
    - Sección por CADA consulta (tipo -> análisis 2 líneas + capturas 1 o 2)
    - Conclusión final
    Retorna: {'report_path': str, 'included': {tipo: [paths...]}}
    """
    _safe_dir(out_dir)
    tipo_alerta = (meta or {}).get("tipo_alerta", "").strip() or "Alerta"
    fecha_alerta = (meta or {}).get("fecha_alerta", "") or ""
    monto_usd = (meta or {}).get("monto_usd", None)

    # Preparar items -> (tipo, [capturas...])
    items: List[Tuple[str, List[str]]] = []
    included: Dict[str, List[str]] = {}
    for tipo, payload in (results or {}).items():
        if not isinstance(payload, dict):
            continue
        shots = []
        p1 = payload.get("screenshot_path")
        if p1 and os.path.exists(p1):
            shots.append(p1)
        p2 = payload.get("screenshot_historial_path")
        if p2 and os.path.exists(p2):
            shots.append(p2)
        if shots:
            items.append((tipo, shots))
            included[tipo] = shots

    # Análisis por LLM (opcional) o fallback
    analisis_por_pagina, conclusion = _try_llm_analysis(tipo_alerta, monto_usd, fecha_alerta, items)

    # Construir DOCX
    doc = Document()

    # Estilo base
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    # Portada simple
    title = doc.add_heading(f"Informe de Verificación — {tipo_alerta}", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.add_run(f"Monto: {_fmt_money(monto_usd)}   |   Fecha de alerta: {fecha_alerta}").italic = True

    doc.add_paragraph()  # espacio

    # Cuerpo por consulta
    for tipo, shots in items:
        doc.add_heading(tipo.replace("_", " ").title(), level=2)
        analisis = analisis_por_pagina.get(tipo) or "Se adjuntan evidencias. Revisión manual requerida."
        doc.add_paragraph(analisis)

        for spath in shots:
            _insert_image(doc, spath, max_width_in=6.0)
            # pequeño pie de imagen:
            cap = doc.add_paragraph()
            cap.add_run(os.path.basename(spath)).italic = True

        doc.add_paragraph()  # espacio

    # Conclusión
    doc.add_heading("Conclusión", level=2)
    doc.add_paragraph(conclusion)

    # Guardar
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    short_tipo = "".join(c for c in tipo_alerta.lower() if c.isalnum())[:20] or "alerta"
    fname = f"informe_{short_tipo}_{ts}.docx"
    out_path = os.path.join(out_dir, fname)
    doc.save(out_path)

    return {"report_path": os.path.abspath(out_path), "included": included}
