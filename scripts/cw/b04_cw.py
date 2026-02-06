import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from pathlib import Path

def procesar_csv_y_transformar(carpeta_entrada, carpeta_base_salida, fecha_inicio=None, fecha_fin=None):
    """
    Procesa archivos CSV de una carpeta, restando 5 horas a la columna 'sent_at',
    luego transforma y divide por ejecutivo, guardando los resultados en una carpeta
    con la fecha actual.
    """
    # Mapa de inbox_id a Ejecutivo
    mapa_ejecutivos = {
        7: 'Eduardo',
        4: 'Jennifer',
        12: 'Nicol',
        13: 'Sheyla'
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
        print("No se encontraron conversaciones para los inboxes especificados.")
        return

    # Filtrar solo mensajes reales (excluir mensajes del sistema)
    # message_type: 0=incoming (del contacto), 1=outgoing (del agente), 2=activity (sistema)
    df_clean = df_filtrado[df_filtrado['message_type'].isin([0, 1])].copy()

    # Asignar el nombre del ejecutivo basado en el inbox_id
    df_clean['Ejecutivo'] = df_clean['inbox_id'].map(mapa_ejecutivos)

    # Crear ID_LEAD desde contact_phone
    df_clean['ID_LEAD'] = df_clean['contact_phone']

    # Crear ID_LEAD_CW desde conversation_id
    df_clean['ID_LEAD_CW'] = df_clean['conversation_id']

    # Convertir sent_at a datetime
    df_clean['Fecha_Hora'] = pd.to_datetime(df_clean['sent_at'])

    # Determinar tipo de mensaje
    # message_type: 0 = Contact (Entrante), 1 = User (Saliente)
    df_clean['Tipo_Mensaje'] = df_clean['message_type'].map({
        0: 'Entrante',
        1: 'Saliente'
    })

    # Manejar contenido: si está vacío pero hay archivo adjunto, indicarlo
    def obtener_contenido(row):
        contenido = str(row['content']) if pd.notna(row['content']) else ''
        
        # Si el contenido está vacío o es muy corto, verificar si hay adjunto
        if (contenido == '' or contenido == 'nan' or len(contenido.strip()) < 2) and pd.notna(row['file_mime']):
            # Determinar tipo de archivo
            mime = str(row['file_mime']).lower()
            
            if 'image' in mime:
                return '[📷 Imagen]'
            elif 'pdf' in mime:
                return '[📄 PDF]'
            elif 'video' in mime:
                return '[🎥 Video]'
            elif 'audio' in mime:
                return '[🎵 Audio]'
            elif 'application' in mime or 'document' in mime:
                return '[📎 Documento]'
            else:
                return '[📎 Archivo adjunto]'
        
        return contenido.strip()

    df_clean['Contenido_Mensaje'] = df_clean.apply(obtener_contenido, axis=1)

    # Calcular secuencia por conversación
    df_clean = df_clean.sort_values(['conversation_id', 'Fecha_Hora'])
    df_clean['Secuencia'] = df_clean.groupby('conversation_id').cumcount() + 1

    # Seleccionar y renombrar columnas finales
    df_final = df_clean[[
        'message_id',
        'ID_LEAD',
        'ID_LEAD_CW',
        'Ejecutivo',
        'Fecha_Hora',
        'Tipo_Mensaje',
        'Contenido_Mensaje',
        'Secuencia',
        'contact_name',
        'contact_email'
    ]].copy()

    # Renombrar para que sea más claro
    df_final.columns = [
        'ID_Mensaje',
        'ID_LEAD',
        'ID_LEAD_CW',
        'Ejecutivo',
        'Fecha_Hora',
        'Tipo_Mensaje',
        'Contenido_Mensaje',
        'Secuencia',
        'Nombre_Contacto',
        'Email_Contacto'
    ]

    # Ordenar por conversación y secuencia
    df_final = df_final.sort_values(['ID_LEAD_CW', 'Secuencia'])

    # Guardar tabla detallada
    output_path = os.path.join(carpeta_salida, 'mensajes_detallados_powerbi.csv')
    df_final.to_csv(output_path, index=False, encoding='utf-8-sig')

    # Crear también tabla resumen (agregada por conversación)
    resumen = df_clean.groupby(['conversation_id', 'ID_LEAD', 'Ejecutivo']).agg({
        'message_id': 'count',  # Total de mensajes
        'Fecha_Hora': ['min', 'max']  # Primer y último mensaje
    }).reset_index()

    resumen.columns = ['ID_LEAD_CW', 'ID_LEAD', 'Ejecutivo', 'Total_Mensajes', 
                       'Primer_Mensaje', 'Ultimo_Mensaje']

    # Contar mensajes por tipo
    mensajes_entrantes = df_clean[df_clean['Tipo_Mensaje']=='Entrante'].groupby('conversation_id').size()
    mensajes_salientes = df_clean[df_clean['Tipo_Mensaje']=='Saliente'].groupby('conversation_id').size()

    resumen['Mensajes_Cliente'] = resumen['ID_LEAD_CW'].map(mensajes_entrantes).fillna(0).astype(int)
    resumen['Mensajes_Vendedor'] = resumen['ID_LEAD_CW'].map(mensajes_salientes).fillna(0).astype(int)

    # Calcular duración de conversación en minutos
    resumen['Duracion_Conversacion_Min'] = (
        (resumen['Ultimo_Mensaje'] - resumen['Primer_Mensaje']).dt.total_seconds() / 60
    ).round(2)

    # Calcular ratio vendedor/cliente
    resumen['Ratio_Vendedor_Cliente'] = (
        resumen['Mensajes_Vendedor'] / resumen['Mensajes_Cliente'].replace(0, np.nan)
    ).round(2)

    # Agregar nombre y email del contacto
    contactos_info = df_clean.groupby('conversation_id').agg({
        'contact_name': 'first',
        'contact_email': 'first'
    }).reset_index()

    resumen = resumen.merge(
        contactos_info,
        left_on='ID_LEAD_CW',
        right_on='conversation_id',
        how='left'
    )

    resumen = resumen.drop('conversation_id', axis=1)
    resumen.columns = ['ID_LEAD_CW', 'ID_LEAD', 'Ejecutivo', 'Total_Mensajes', 
                       'Primer_Mensaje', 'Ultimo_Mensaje', 'Mensajes_Cliente', 
                       'Mensajes_Vendedor', 'Duracion_Conversacion_Min', 
                       'Ratio_Vendedor_Cliente', 'Nombre_Contacto', 'Email_Contacto']

    # Guardar resumen
    output_resumen = os.path.join(carpeta_salida, 'resumen_conversaciones_powerbi.csv')
    resumen.to_csv(output_resumen, index=False, encoding='utf-8-sig')

    # Mantener la lógica original para archivos individuales por ejecutivo
    conversaciones = df_clean.groupby('conversation_id')

    resultados = []

    for conversation_id, grupo in conversaciones:
        grupo = grupo.sort_values(by='sent_at').reset_index(drop=True)
        
        # Encontrar el primer mensaje real (no asignación automática)
        primer_mensaje_real = None
        for idx, mensaje in grupo.iterrows():
            content = str(mensaje.get('content', ''))
            sender_type = mensaje.get('sender_type')
            
            # Saltar asignaciones automáticas
            if 'Asignado a' in content and 'por Automation System' in content:
                continue
            
            # Este es el primer mensaje real
            primer_mensaje_real = mensaje
            break
        
        # Si no hay mensajes reales, continuar
        if primer_mensaje_real is None:
            continue
            
        primer_mensaje = primer_mensaje_real

        if str(primer_mensaje['contact_name']).strip().endswith('(GROUP)'):
            continue

        fecha_primer_mensaje = primer_mensaje['sent_at']
        if fecha_inicio and fecha_primer_mensaje < pd.to_datetime(fecha_inicio):
            continue
        if fecha_fin and fecha_primer_mensaje > pd.to_datetime(fecha_fin):
            continue

        mensaje_entrante = 'si' if primer_mensaje['sender_type'] == 'Contact' else 'no'

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
            'Hora Saliente': hora_saliente,
            'ID_LEAD_cw': conversation_id,
            'contact_phone': primer_mensaje.get('contact_phone', ''),
            'contact_name': primer_mensaje.get('contact_name', '')
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
