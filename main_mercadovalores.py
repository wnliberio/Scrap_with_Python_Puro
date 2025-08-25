# main_mercadovalores.py
import argparse, json
from flows.mercado_valores import run_mercado_valores

def main():
    parser = argparse.ArgumentParser(description="Prueba aislada: Supercias Mercado de Valores")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("-i", "--ident", type=str, help="Identificación/RUC (p.ej. 1792996325001)")
    g.add_argument("-n", "--nombre", type=str, help='Nombre de la entidad (p.ej. "CEDEGUIM S.A.")')

    parser.add_argument("-m", "--mode", type=str, default="auto", choices=["auto", "ident", "nombre"],
                        help="Modo de búsqueda (auto: detecta por dígitos)")
    parser.add_argument("--solve", action="store_true",
                        help="Si se indica, resuelve el captcha con Azure y devuelve captura final de resultados.")
    parser.add_argument("-H", "--headless", type=int, default=0, help="1=headless, 0=visible")
    args = parser.parse_args()

    query = args.ident or args.nombre
    data = run_mercado_valores(query, mode=args.mode, headless=bool(args.headless), solve=args.solve)
    print(json.dumps(data or {"screenshot_path": None}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

