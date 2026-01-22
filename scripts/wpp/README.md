# Scripts de WhatsApp Web Processing (WPP)

Esta carpeta contiene scripts para la extracción y procesamiento de datos de WhatsApp Web.

## 📁 Archivos Principales

### 🤖 **b01_s.py** - Scraper Básico
Script de extracción de mensajes con configuración estándar.

**Características:**
- **Límite de chats**: 200 chats no-grupo
- **Timeout por chat**: 40 segundos
- **Manejo de timeouts**: Si hay timeout, **NO guarda** los mensajes recolectados
- **Lista de excluidos**: Incluye contactos específicos y números de teléfono
- **Debug**: Incluye logs de depuración

**Uso:**
```bash
python b01_s.py
```

**Configuración:**
- Perfil: wpp1..wpp6 (seleccionable al ejecutar)
- Input: `files/input/wpp/`
- Output: Archivo CSV en `files/input/wpp/`

---

### ⚡ **b02_omar.py** - Scraper Optimizado
Versión mejorada con mejor manejo de errores y recuperación de datos.

**Características:**
- **Límite de chats**: 5 chats no-grupo (más conservador)
- **Timeout por chat**: 20 segundos
- **Manejo de timeouts**: Si hay timeout, **SÍ guarda** los mensajes recolectados hasta ese momento
- **Lista de excluidos**: Más corta, enfocada en grupos principales
- **Reporte de timeouts**: Muestra lista de chats que alcanzaron timeout

**Mejoras sobre b01_s.py:**
- ✅ Recupera datos incluso con timeouts
- ✅ Menos tiempo de espera entre acciones
- ✅ Mejor manejo de errores
- ✅ Reporte detallado de chats con problemas

**Uso:**
```bash
python b02_omar.py
```

---

### 🔄 **b03_p.py** - Procesador de Datos
Script que convierte los datos crudos del scraper en formato estructurado.

**Características:**
- **Parseo inteligente de fechas**: Detecta automáticamente formato D/M vs M/D
- **Normalización de espacios**: Maneja NBSP y caracteres especiales
- **Conversión a 24h**: Transforma AM/PM a formato 24 horas
- **Procesamiento por conversación**: Agrupa mensajes por contacto
- **Detección de entrantes/salientes**: Identifica quién inició la conversación

**Lógica de procesamiento:**
1. **Mensaje entrante**: Primer mensaje de cliente (no-owner)
2. **Mensaje saliente**: Primera respuesta del ejecutivo (owner)
3. **Outbound**: Si el ejecutivo inicia la conversación

**Autores reconocidos (owner):**
- Tú, You, Me
- Nombre del ejecutivo (del archivo)
- Nombres completos de asesores

**Uso:**
```bash
python b03_p.py
```

**Input/Output:**
- Input: `files/input/wpp/{ejecutivo}.csv`
- Output: `files/output/{ejecutivo}.csv`

---

##  **Flujo de Trabajo Típico**

### Opción 1: Scraper + Procesador
```bash
# 1. Extraer datos con scraper optimizado
python b02_omar.py

# 2. Procesar datos extraídos
python b03_p.py
```

### Opción 2: Procesamiento Directo
```bash
# Procesar datos ya extraídos
python b03_p.py
```

---

## 📁 **Estructura de Carpetas**

```
files/
├── input/wpp/           # CSVs crudos del scraper
├── intermediate/        # Datos procesados intermedios
└── output/             # Reportes finales por ejecutivo
```

---

## ⚙️ **Configuración Común**

### Perfiles de Chrome
- **wpp1** a **wpp6**: Perfiles independientes para evitar conflictos
- **Ubicación**: `~/whatsapp_selenium_profiles/`

### Variables Clave
- `MAX_NON_GROUP_CHAT`: Límite de chats a procesar
- `CHAT_TIME_LIMIT_SECONDS`: Timeout por chat
- `EXCLUDE_TITLES`: Lista de chats a omitir

---

## 🔧 **Requisitos**

Ver `requirements.txt` para dependencias:

```bash
pip install -r requirements.txt
```

**Paquetes principales:**
- `selenium` - Automatización web
- `webdriver-manager` - Gestión de ChromeDriver
- `pandas` - Procesamiento de datos
- `python-dateutil` - Manejo de fechas

---

## 🐛 **Solución de Problemas**

### Issues Comunes

**1. ChromeDriver no encontrado**
```bash
# El webdriver-manager lo descarga automáticamente
# Si falla, limpiar caché:
rm -rf ~/.wdm/drivers/
```

**2. Timeout en chats**
- **b01_s.py**: Pierde los datos del chat con timeout
- **b02_omar.py**: Recupera datos parciales con timeout

**3. Fechas mal interpretadas**
- **b03_p.py**: Usa parseo inteligente D/M vs M/D
- Asume formato español (D/M) por defecto

**4. Permisos de WhatsApp**
- Escanear QR al inicio
- Esperar carga completa antes de continuar

---

## 📈 **Mejoras Sugeridas**

### Para b01_s.py → b02_omar.py
- ✅ Reducir tiempos de espera
- ✅ Extraer el timestamp de archivos adjuntos y audios

### Para b03_p.py
- 🔄 Agregar soporte para múltiples ejecutivos
- 📊 Generar métricas adicionales
- 🔍 Mejorar detección de outliers

---

## 📞 **Soporte**

Para problemas o dudas:
1. Revisar logs de ejecución
2. Verificar estructura de archivos CSV
3. Validar configuración de perfiles
4. Consultar `requirements.txt` para dependencias
