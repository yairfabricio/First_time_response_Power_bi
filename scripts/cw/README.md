# Script de Chatwoot Processing (CW)

Esta carpeta contiene el script principal para el procesamiento integrado de datos de Chatwoot.

## 📁 Archivo Principal

### ⚡ **b04_cw.py** - Procesador Integrado de Chatwoot
Script que procesa archivos CSV de Chatwoot desde el estado crudo hasta el formato final en un solo paso.

**Características:**
- **Proceso unificado**: Lee CSVs crudos y genera reportes finales
- **Ajuste de tiempo**: Resta 5 horas a la columna `sent_at`
- **Mapeo de ejecutivos**: Asigna ejecutivos según inbox_id
- **Carpeta con fecha**: Crea automáticamente carpeta con fecha actual
- **División por ejecutivo**: Genera un CSV por cada ejecutivo
- **Sin archivos intermedios**: Va directo del input al output final

**Mapeo de ejecutivos:**
```python
mapa_ejecutivos = {
    7: 'Eduardo',
    3: 'Karina', 
    4: 'Jennifer'
}
```

**Uso:**
```bash
python b04_cw.py
```

**Configuración:**
- Input: `files/input/cw/`
- Output: `files/output/{YYYY-MM-DD}/`

**Funcionalidad principal:**
```python
procesar_csv_y_transformar(carpeta_entrada, carpeta_base_salida, fecha_inicio, fecha_fin)
```

---

## 📁 **Estructura de Carpetas**

```
files/
├── input/cw/            # CSVs crudos de Chatwoot
└── output/             # Reportes finales por ejecutivo y fecha
    ├── 2026-01-21/    # Carpeta con fecha actual
    ├── Eduardo.csv
    ├── Karina.csv
    └── Jennifer.csv
```

---

## ⚙️ **Configuración Clave**

### Variables de Tiempo
- **Ajuste horario**: -5 horas (restar a sent_at)
- **Zona horaria**: Ajuste para UTC a local

### Mapeo de Ejecutivos
- **inbox_id 7**: Eduardo
- **inbox_id 3**: Karina
- **inbox_id 4**: Jennifer

### Filtros de Conversación
- **Inboxes procesados**: 3, 4, 7
- **Grupos excluidos**: Conversaciones que terminan en "(GROUP)"
- **Mensajes de sistema**: "Asignado a ... por Automation System"

---

## 🔧 **Requisitos**

Ver `requirements.txt` para dependencias:

```bash
pip install -r requirements.txt
```

**Paquetes principales:**
- `pandas` - Procesamiento de DataFrames
- `pathlib` - Manejo de rutas de archivos
- `datetime` - Manejo de fechas y horas

---

## 📊 **Formato de Datos**

### Input (CSVs Crudos)
```csv
conversation_id,inbox_id,sender_type,sent_at,contact_name,content
12345,7,User,2026-01-21 14:30:00,Cliente Test,Hola, necesito información
```

### Output (CSVs por Ejecutivo)
```csv
Ejecutivo,ID_LEAD,Mensaje Entrante,Mensaje Saliente,Fecha Entrante,Hora Entrante,Fecha Saliente,Hora Saliente
Eduardo,12345,SI,SI,2026-01-21,09:30:00,2026-01-21,09:35:00
```

---

## 🐛 **Solución de Problemas**

### Issues Comunes

**1. Columna 'sent_at' no encontrada**
```
Advertencia: El archivo 'archivo.csv' no contiene la columna 'sent_at'. Se omitirá.
```
- **Solución**: Verificar que los CSVs de Chatwoot tengan la columna `sent_at`

**2. No hay conversaciones para los inboxes especificados**
```
No se encontraron conversaciones para los inboxes especificados (3, 4, 7).
```
- **Solución**: Revisar IDs de inbox en el CSV original

**3. Fechas inválidas después del ajuste**
- **Solución**: Verificar formato de fecha en CSV original (debe ser YYYY-MM-DD HH:MM:SS)

**4. Carpeta de salida no se crea**
- **Solución**: Verificar permisos de escritura en `files/output/`

---

## 📈 **Mejoras Sugeridas**

### Para b04_cw.py
- 🔄 Agregar soporte para múltiples carpetas de input
- 📊 Generar métricas de procesamiento
- 🔍 Mejor manejo de errores por archivo

---

## 📞 **Soporte**

Para problemas o dudas:
1. Verificar estructura de archivos CSV
2. Validar configuración de rutas
3. Revisar logs de ejecución
4. Consultar `requirements.txt` para dependencias
