# main_funcion_judicial.py
import argparse, json
from flows.funcion_judicial import process_funcion_judicial
from core.utils.log import log
from core.utils.tee import start_tee, stop_tee
from core.config import LOG_FILE

def main():
    ap = argparse.ArgumentParser(description="Consulta Función Judicial con captura de procesos judiciales.")
    ap.add_argument("--nombres", nargs="+", help="Uno o más nombres completos (Apellidos Nombres).")
    ap.add_argument("--headless", action="store_true", help="Headless (no recomendado para debugging de la secuencia especial de clics).")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--log", dest="log", action="store_true", help="Activa log a archivo (por defecto).")
    g.add_argument("--no-log", dest="log", action="store_false", help="Desactiva log a archivo.")
    ap.set_defaults(log=True)

    args = ap.parse_args()

    if args.log:
        start_tee(append=True)
        log(f"\nBitácora activa: {LOG_FILE}")

    try:
        nombres_list = args.nombres or ["Vela Vasco Marco Antonio"]  # ejemplo por defecto
        headless = bool(args.headless)

        for idx, nombres in enumerate(nombres_list, 1):
            log(f"\n[{idx}/{len(nombres_list)}] FUNCIÓN JUDICIAL objetivo: {nombres}")
            data = process_funcion_judicial(nombres, headless=headless)
            print(json.dumps({"nombres": nombres, "result": data}, ensure_ascii=False, indent=2))

        log("\n🏁 Proceso FUNCIÓN JUDICIAL completado.")
    finally:
        if args.log:
            stop_tee()

if __name__ == "__main__":
    main()