# main_google.py
import argparse, json
from flows.google_search import run_google_search

def main():
    parser = argparse.ArgumentParser(description="Prueba aislada: Google Search")
    parser.add_argument("-q", "--query", required=True, help='Texto a buscar (p. ej.: "VELA VASCO MARCO ANTONIO")')
    parser.add_argument("-H", "--headless", type=int, default=0, help="1=headless, 0=visible")
    args = parser.parse_args()

    data = run_google_search(args.query.strip(), headless=bool(args.headless))
    print(json.dumps(data or {"screenshot_path": None}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
