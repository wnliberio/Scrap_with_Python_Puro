
# main_mercadovalores.py
import argparse
import json

from flows.mercado_valores import run_mercado_valores_stage1

def main():
    parser = argparse.ArgumentParser(
        description="Prueba aislada – Supercias: Mercado de Valores (Etapa 1: capturar captcha)"
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("-i", "--ident", type=str, help="Identificación/RUC (10–13 dígitos)")
    g.add_argument("-n", "--nombre", type=str, help="Nombre de la entidad")

    parser.add_argument("-H", "--headless", type=int, default=0, help="1=headless, 0=visible")

    args = parser.parse_args()

    if args.ident:
        valor = args.ident.strip()
        modo = "ident"
    else:
        valor = args.nombre.strip()
        modo = "nombre"

    data = run_mercado_valores_stage1(valor, modo=modo, headless=bool(args.headless))
    print(json.dumps(data or {"captcha_path": None}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
