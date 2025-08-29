- DESDE EL FRONTEND
  Execute Back: uvicorn app.main:app --reload --port 8000
  Execute front: npm run dev

- PROBAR COMO SI FUERA DESDE FRONT PERO ENVIANDO DATOS DESDE POWERSHELL
  $headers = @{ "Content-Type" = "application/json" }
$body = @{
  items = @(
  @{ tipo = "ruc"; valor = "2300531528001" },
  @{ tipo = "deudas"; valor = "2300531528001" }
  )
  modo = "async"
  headless = $false
  } | ConvertTo-Json -Depth 3

                            Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/consultas" -Method POST -Headers $headers -Body $body

- PROBAR SOLO "denuncias" POR CLI EJECUTANDO DESDE BACK
  python main_denuncias.py --nombres "VELA VASCO MARCO ANTONIO"

- PROBAR SOLO "mercado valores" POR CLI, Terminal VSCode EJECUTANDO DESDE BACK sin Solver de Captcha OCR

Por Identificacion: python main_mercadovalores.py -i 1792996325001

Por Nombre: python main_mercadovalores.py -n "CEDEGUIM S.A."

- PROBAR CON OCR SOLO "mercado valores" POR CLI, Terminal VSCode EJECUTANDO DESDE BACK
  Por Identificacion: python main_mercadovalores.py -i 1792996325001 --solve
  Por Nombre: python main_mercadovalores.py -n "CEDEGUIM S.A." --solve
  Con código manual captcha: python main_mercadovalores.py -i 1792996325001 --solve --captcha 123ABC

- CÓMO PROBAR (Predio Manta)

  # Ejemplo con Cédula

  python main_predio_manta.py -v 1800587626

  # Ejemplo con Nombre

  python main_predio_manta.py -v "VELA VASCO MARCO ANTONIO"

  # En headless (si tu stack lo permite)

  python main_predio_manta.py -v 1800587626 -H 1

- CÓMO PROBAR (Quito)
  # Ejemplo con Cédula
  python main_predio_quito.py -n "VELA VASCO MARCO ANTONIO"
  # Headless:
  python main_predio_quito.py -n "VELA VASCO MARCO ANTONIO" -H 1
