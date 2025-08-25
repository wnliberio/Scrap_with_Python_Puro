from typing import Dict, Any, List
from time import sleep
from core.utils.log import log

from flows.ruc import process_ruc
from flows.deudas import process_deudas
from flows.denuncias import process_denuncias
from flows.mercado_valores import run_mercado_valores 
from flows.interpol import run_interpol_search

from app.models.schemas import QueryItem
from core.config import INTER_ITEM_DELAY_SECONDS


def _parse_interpol_valor(valor: str) -> (str, str):
    """
    Acepta:
      - 'APELLIDOS|NOMBRES'
      - 'APELLIDOS|'
      - '|NOMBRES'
      - 'APELLIDOS' (sin '|')
    Retorna (apellidos, nombres) ya normalizados.
    """
    v = (valor or "").strip()
    if "|" in v:
        a, b = v.split("|", 1)
        return " ".join(a.split()), " ".join((b or "").split())
    return " ".join(v.split()), ""


def run_items(items: List[QueryItem], headless: bool = False) -> Dict[str, Any]:
    """
    Ejecuta en SECUENCIA solo los items recibidos.
    Retorna dict tipo -> payload.
    """
    results: Dict[str, Any] = {}
    for index, it in enumerate(items, start=1):
        tipo = it.tipo.lower()
        valor = it.valor.strip()
        log(f"⚙️ Ejecutando item {index}/{len(items)}: {tipo} → {valor}")

        if tipo == "ruc":
            res = process_ruc(valor, headless=headless)
            results["ruc"] = res

        elif tipo == "deudas":
            res = process_deudas(valor, headless=headless)
            results["deudas"] = res

        elif tipo == "denuncias":
            res = process_denuncias(valor, headless=headless)
            results["denuncias"] = res

        elif tipo == "mercado_valores":
            # Auto: si solo dígitos, validar 13.
            if valor.isdigit() and len(valor) != 13:
                results["mercado_valores"] = {"error": "El RUC debe tener exactamente 13 dígitos."}
            else:
                res = run_mercado_valores(valor, mode="auto", headless=headless, solve=True)
                results["mercado_valores"] = res

        elif tipo == "interpol":
            # Libre elección: apellidos o nombres o ambos.
            ap = (getattr(it, "apellidos", None) or "").strip()
            no = (getattr(it, "nombres", None) or "").strip()

            # Compatibilidad: si no llegaron apellidos/nombres, usar 'valor' como apellidos.
            if not ap and not no:
                ap = valor

            if not ap and not no:
                results["interpol"] = {"error": "INTERPOL: ingresa al menos Apellidos o Nombres."}
            else:
                res = run_interpol_search(apellidos_o_full=ap, nombres=no, headless=headless)
                results["interpol"] = res

        else:
            results[tipo] = {"error": f"Tipo no soportado: {tipo}"}

        if index < len(items):
            log(f"⏳ Esperando {INTER_ITEM_DELAY_SECONDS}s antes del siguiente item…")
            sleep(INTER_ITEM_DELAY_SECONDS)

    return results