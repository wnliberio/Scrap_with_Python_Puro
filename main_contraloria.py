# main_contraloria.py
import argparse, json
from flows.contraloria_ddjj import run_contraloria_ddjj

def main():
    parser = argparse.ArgumentParser(description="Prueba aislada: Contraloría – Declaraciones juradas (Últimas)")
    parser.add_argument("-c", "--cedula", required=True, help="Cédula (exactamente 10 dígitos)")
    parser.add_argument("--solve", action="store_true", help="Resolver captcha con Azure y tomar captura final")
    parser.add_argument("-H", "--headless", type=int, default=0, help="1=headless, 0=visible")
    args = parser.parse_args()

    data = run_contraloria_ddjj(args.cedula.strip(), solve=bool(args.solve), headless=bool(args.headless))
    print(json.dumps(data or {"screenshot_path": None}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
