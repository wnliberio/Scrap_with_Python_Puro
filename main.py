# main.py
import argparse, json, sys
from flows.ruc import process_ruc
from core.utils.log import log

def main():
    ap = argparse.ArgumentParser(description="Consulta RUC (SRI) con captura final de pantalla.")
    ap.add_argument("--ruc", nargs="+", help="Uno o más RUC a consultar (se procesan secuencialmente).")
    ap.add_argument("--headless", action="store_true", help="Headless. NO recomendado por captcha/pyautogui.")
    args = ap.parse_args()

    rucs = args.ruc or ["2300142457001"]  # <-- cambia por el que quieras si no pasas --ruc
    headless = bool(args.headless)

    for idx, ruc in enumerate(rucs, 1):
        log(f"\n[{idx}/{len(rucs)}] RUC objetivo: {ruc}")
        data = process_ruc(ruc, headless=headless)
        print(json.dumps({ "ruc": ruc, "result": data }, ensure_ascii=False, indent=2))

    log("\n🏁 Proceso completado.")

if __name__ == "__main__":
    main()
