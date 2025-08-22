# main_antecedentes.py
import argparse, json
from flows.antecedentes import process_antecedentes
from core.utils.log import log
from core.utils.tee import start_tee, stop_tee
from core.config import LOG_FILE

def main():
    ap = argparse.ArgumentParser(description="Certificado de Antecedentes (Min. Interior) con captura final.")
    ap.add_argument("--cedula", help="Cédula (10 dígitos).")
    ap.add_argument("--headless", action="store_true", help="Headless (no recomendado por captcha).")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--log", dest="log", action="store_true", help="Activa log a archivo (por defecto).")
    g.add_argument("--no-log", dest="log", action="store_false", help="Desactiva log a archivo.")
    ap.set_defaults(log=True)

    args = ap.parse_args()

    if args.log:
        start_tee(append=True)
        log(f"\nBitácora activa: {LOG_FILE}")

    try:
        ced = args.cedula or "2300531528"  # ejemplo
        headless = bool(args.headless)

        log(f"\n[1/1] ANTECEDENTES objetivo: {ced}")
        data = process_antecedentes(ced, headless=headless)
        print(json.dumps({"cedula": ced, "result": data}, ensure_ascii=False, indent=2))
        log("\n🏁 Proceso ANTECEDENTES completado.")
    finally:
        if args.log:
            stop_tee()

if __name__ == "__main__":
    main()
