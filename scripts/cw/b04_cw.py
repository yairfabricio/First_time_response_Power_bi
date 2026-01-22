import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path

def procesar_csv_y_transformar(carpeta_entrada, carpeta_base_salida, fecha_inicio=None, fecha_fin=None):
    """
    Procesa archivos CSV de una carpeta, restando 5 horas a la columna 'sent_at',
    luego transforma y divide por ejecutivo, guardando los resultados en una carpeta
eta con la fecha actual.
    """
    # Mapa de inbox_id a Ejecutivo
    mapa_ejecutivos = {
        7: 'Eduardo',
        3: 'Karina',
        4: 'Jennifer'
    }
    inboxes_a_procesar = list(mapa_ejecutivos.keys())

    # Crear carpeta de salida con fecha actual
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    carpeta_salida = os.path.join(carpeta_base_salida, fecha_actual)
    Path(carpeta_salida).mkdir(parents=True, exist_ok=True)
    
    # Verificar si la carpeta de entrada existe
    if not os.path.exists(carpeta_entrada):
        print(f"Error: La carpeta de entrada '{carpeta_entrada}' no existe.")
        return
    
    # Obtener lista de archivos CSV en la carpeta de entrada
    archivos_csv = [f for f in os.listdir(carpeta_entrada) if f.lower().endswith('.csv')]
    
    if not archivos_csv:
        print(f"No se encontraron archivos CSV en '{carpeta_entrada}'")
        return
    
    print(f"Procesando {len(archivos_csv)} archivos CSV...")
    
    # Combinar todos los CSV procesados en un solo DataFrame
    df_combinado = pd.DataFrame()
    
    for archivo in archivos_csv:
        ruta_entrada = os.path.join(carpeta_entrada, archivo)
        
        try:
            # Leer el archivo CSV
            df = pd.read_csv(ruta_entrada)
            
            # Verificar si existe la columna 'sent_at'
            if 'sent_at' not in df.columns:
                print(f"Advertencia: El archivo '{archivo}' no contiene la columna 'sent_at'. Se omitirá.")
                continue
            
            # Convertir la columna 'sent_at' a datetime
            try:
                df['sent_at'] = pd.to_datetime(df['sent_at'])
            except Exception as e:
                print(f"Error al convertir fechas en '{archivo}': {e}")
                continue
            
            # Restar 5 horas
            df['sent_at'] = df['sent_at'] - timedelta(hours=5)
            
            # Agregar al DataFrame combinado
            df_combinado = pd.concat([df_combinado, df], ignore_index=True)
            print(f"✓ Procesado: {archivo}")
            
        except Exception as e:
            print(f"Error al procesar '{archivo}': {e}")
    
    if df_combinado.empty:
        print("No se pudo procesar ningún archivo válido.")
        return
    
    print(f"\nIniciando transformación de datos combinados...")
    
    # Filtrar solo los inboxes que nos interesan
    df_filtrado = df_combinado[df_combinado['inbox_id'].isin(inboxes_a_procesar)]
    if df_filtrado.empty:
        print("No se encontraron conversaciones para los inboxes especificados (3, 4, 7).")
        return

    # Asignar el nombre del ejecutivo basado en el inbox_id
    df_filtrado['Ejecutivo'] = df_filtrado['inbox_id'].map(mapa_ejecutivos)

    # Agrupar por conversación y ordenar por fecha
    conversaciones = df_filtrado.groupby('conversation_id')

    resultados = []

    for conversation_id, grupo in conversaciones:
        grupo = grupo.sort_values(by='sent_at').reset_index(drop=True)
        primer_mensaje = grupo.iloc[0]

        if str(primer_mensaje['contact_name']).strip().endswith('(GROUP)'):
            continue

        fecha_primer_mensaje = primer_mensaje['sent_at']
        if fecha_inicio and fecha_primer_mensaje < pd.to_datetime(fecha_inicio):
            continue
        if fecha_fin and fecha_primer_mensaje > pd.to_datetime(fecha_fin):
            continue

        mensaje_entrante = 'si' if 'Asignado a' in str(primer_mensaje['content']) and 'por Automation System' in str(primer_mensaje['content']) else 'no'

        primera_respuesta = grupo[(grupo['sender_type'] == 'User') & (grupo.index > 0)]
        mensaje_saliente = 'no'
        fecha_saliente = None
        hora_saliente = None

        if not primera_respuesta.empty:
            mensaje_saliente = 'si'
            fecha_saliente = primera_respuesta.iloc[0]['sent_at'].date()
            hora_saliente = primera_respuesta.iloc[0]['sent_at'].time()

        resultados.append({
            'Ejecutivo': primer_mensaje['Ejecutivo'],
            'ID_LEAD': conversation_id,
            'Mensaje Entrante': mensaje_entrante,
            'Mensaje Saliente': mensaje_saliente,
            'Fecha Entrante': primer_mensaje['sent_at'].date(),
            'Hora Entrante': primer_mensaje['sent_at'].time(),
            'Fecha Saliente': fecha_saliente,
            'Hora Saliente': hora_saliente
        })

    if not resultados:
        print("No se generaron resultados tras el procesamiento.")
        return

    df_resultado = pd.DataFrame(resultados)

    # Dividir y guardar por ejecutivo
    for ejecutivo, datos_ejecutivo in df_resultado.groupby('Ejecutivo'):
        nombre_archivo = f"{ejecutivo}.csv"
        ruta_salida_archivo = os.path.join(carpeta_salida, nombre_archivo)
        datos_ejecutivo.to_csv(ruta_salida_archivo, index=False)
        print(f"Guardado archivo para {ejecutivo}: {ruta_salida_archivo}")

    print(f"\nProceso completado. Archivos guardados en: {carpeta_salida}")

if __name__ == "__main__":
    # Configuración de carpetas
    carpeta_entrada = r"C:\Users\Lima - Rodrigo\Documents\ventas\files\input\cw"  # Cambia esto por tu carpeta de entrada
    carpeta_base_salida = r"C:\Users\Lima - Rodrigo\Documents\ventas\files\output"   # Carpeta base de salida
    
    # Filtro de fechas (opcional, poner None para no usar)
    fecha_inicio = None  # "2026-01-12"
    fecha_fin = None     # "2026-01-18"
    
    # Ejecutar el procesamiento
    procesar_csv_y_transformar(carpeta_entrada, carpeta_base_salida, fecha_inicio, fecha_fin)
