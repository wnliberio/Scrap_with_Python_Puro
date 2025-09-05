# test_insert.py
# Ejecutar este archivo para probar la inserción

try:
    # Importar y probar la función de timezone
    from app.dbb import ec_now_naive, insert_de_lista_records
    
    # Probar que la función de timezone funciona
    print("🕐 Probando función de timezone...")
    hora_actual = ec_now_naive()
    print(f"Hora actual Ecuador: {hora_actual}")
    
    # Insertar los registros
    print("\n📝 Insertando registros...")
    resultado = insert_de_lista_records()
    
    if resultado:
        print("\n✅ ¡Éxito! Todos los registros fueron insertados.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()