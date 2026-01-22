# Script de Processing (b05.py)

Esta carpeta contiene el script principal para el procesamiento y consolidación de datos de conversaciones de Chatwoot/WhatsApp.

## 📁 Archivo Principal

### 🔧 **b05.py** - Procesador de Datos de Conversaciones
Script para consolidar, normalizar y analizar datos históricos de conversaciones de ventas.

**Características:**
- **Lectura de histórico**: Carga archivo base `nuevo_csv.csv` con datos históricos
- **Unión de CSVs**: Combina datos históricos con nuevos CSVs de `files/output/12_18_ene`
- **Normalización de fechas**: Convierte "hoy"/"ayer" y múltiples formatos a YYYY-MM-DD
- **Normalización de horas**: Procesa HH:MM:SS, HH:MM y formatos con milisegundos
- **Cálculo de tiempos**: Calcula tiempo de respuesta entre mensaje entrante y saliente
- **Scoring de respuesta**: Asigna categorías según tiempo de respuesta
- **Segmentación horaria**: Clasifica mensajes por franjas horarias
- **Limpieza de datos**: Elimina duplicados y normaliza nombres de ejecutivos

**Funcionalidades principales:**
```python
# Reemplazar "hoy"/"ayer" y normalizar fechas
_reemplazar_hoy_ayer_y_normalizar(df, cols=("Fecha Entrante", "Fecha Saliente"))

# Unir histórico con nuevos CSVs
construir_df_general_desde_csv(carpetas, df_base=df)

# Calcular tiempo de respuesta
calcular_tiempo_respuesta_hhmmss_nan(df)

# Score de tiempo de respuesta
calcular_score_tiempo_respuesta(df)

# Segmentación horaria
calcular_segmento_horario_entrada(df)
```

**Uso:**
```bash
python b05.py
```

---

## ⚙️ **Configuración Clave**

### Rutas de Datos
- **Histórico**: `files/input/nuevo_csv.csv`
- **Nuevos CSVs**: `files/output/12_18_ene/`
- **Salida**: `files/input/nuevo_csv.csv` (sobrescribe el histórico)

### Columnas Procesadas
- **Fechas**: "Fecha Entrante", "Fecha Saliente"
- **Horas**: "Hora Entrante", "Hora Saliente", "Tiempo Respuesta (min)"
- **Identificación**: "Ejecutivo", "ID_LEAD", "lead_id"
- **Mensajes**: "Mensaje Entrante", "Mensaje Saliente"

### Normalización de Ejecutivos
```python
mapeo = {
    "Carmen": "Karina",
    "JENNIFER": "Jennifer", 
    "Omar": "Omar",
    "Rosmery": "RosmeryPapel",
    "ESTRELLA": "EstrellaCondori",
    "YAMELY": "Yamely"
}
```

---

## 🔧 **Requisitos**

Ver `requirements.txt` para dependencias:

```bash
pip install -r requirements.txt
```

**Paquetes principales:**
- `pandas` - Procesamiento de DataFrames
- `numpy` - Cálculos numéricos y arrays
- `python-dateutil` - Manejo avanzado de fechas
- `unicodedata2` - Normalización de texto con acentos
- `typing-extensions` - Type hints modernos

---

## 📊 **Formato de Datos**

### Input (Histórico + CSVs nuevos)
```csv
Ejecutivo,ID_LEAD,Mensaje Entrante,Mensaje Saliente,Fecha Entrante,Hora Entrante,Fecha Saliente,Hora Saliente
Karina,12345,SI,SI,hoy,09:30:00,hoy,09:35:00
```

### Output (CSV consolidado y procesado)
```csv
Ejecutivo,ID_LEAD,Mensaje Entrante,Mensaje Saliente,Fecha Entrante,Hora Entrante,Fecha Saliente,Hora Saliente,Tiempo Respuesta (min),Score Tiempo Respuesta,Segmento Horario Entrada
Karina,12345,SI,SI,2026-01-22,09:30:00,2026-01-22,09:35:00,00:05:00,🟢 Excelente,☀️ Mañana laborable
```

---

## 🐛 **Solución de Problemas**

### Issues Comunes

**1. Error en formato de fecha**
```
ValueError: time data 'hoy' does not match format '%Y-%m-%d'
```
- **Solución**: El script incluye `_reemplazar_hoy_ayer_y_normalizar()` para manejar estos casos

**2. Duplicados en ID_LEAD**
- **Solución**: El script elimina duplicados con `drop_duplicates(subset=["ID_LEAD"], keep="first")`

**3. Horas con milisegundos**
- **Solución**: `normalizar_hora_col()` maneja formatos HH:MM:SS.mmmmmm

**4. Fechas en formato DD/MM/YYYY**
- **Solución**: La función de normalización detecta y convierte automáticamente

---

## 📈 **Proceso de Ejecución**

### 1. Carga de Histórico
- Lee `nuevo_csv.csv` como base de datos

### 2. Procesamiento de Nuevos CSVs
- Busca CSVs en `files/output/12_18_ene/`
- Normaliza fechas y horas
- Alinea columnas con el histórico

### 3. Consolidación
- Une histórico + nuevos datos
- Elimina duplicados por ID_LEAD
- Ordena por fecha

### 4. Cálculos y Análisis
- Calcula tiempo de respuesta
- Asigna scores por tiempo
- Segmenta por franjas horarias

### 5. Exportación
- Sobrescribe `nuevo_csv.csv` con datos consolidados

---

## 📈 **Mejoras Sugeridas**

### Para b05.py
- 🔄 Agregar más formatos de fecha soportados
- 📊 Generar reportes de procesamiento
- 🔍 Agregar validación de datos de entrada
- 📋 Crear logs detallados del proceso
- 🎯 Soporte para múltiples carpetas de entrada

---

## 📞 **Soporte**

Para problemas o dudas:
1. Verificar que `nuevo_csv.csv` exista en `files/input/`
2. Validar estructura de columnas en CSVs nuevos
3. Revisar instalación de dependencias
4. Consultar `requirements.txt` para versiones específicas
5. Revisar logs de ejecución para errores específicos
