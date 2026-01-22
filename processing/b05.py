# %%%% Cell 0
# importar librerias
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import unicodedata

# %%%% Cell 1
# --- leer el historico: nuevo_csv ---
df=pd.read_csv(r"C:\Users\Lima - Rodrigo\Documents\ventas\files\input\nuevo_csv.csv")

# %%%% Cell 2
# --- dar formato fecha al df --- 
# Fecha Entrante
df["Fecha Entrante"] = pd.to_datetime(
    df["Fecha Entrante"], format="%Y-%m-%d", errors="coerce"
)
df.loc[df["Fecha Entrante"].isna(), "Fecha Entrante"] = np.nan

# Fecha Saliente
df["Fecha Saliente"] = pd.to_datetime(
    df["Fecha Saliente"], format="%Y-%m-%d", errors="coerce"
)
df.loc[df["Fecha Saliente"].isna(), "Fecha Saliente"] = np.nan


# %%%% Cell 3
# --- dar formato hora al df ---
df["Hora Entrante"] = pd.to_datetime(df["Hora Entrante"], format="%H:%M:%S", errors="coerce").dt.time
df["Hora Saliente"] = pd.to_datetime(df["Hora Saliente"], format="%H:%M:%S", errors="coerce").dt.time
df['Tiempo Respuesta (min)'] = pd.to_datetime(df['Tiempo Respuesta (min)'], format="%H:%M:%S", errors = "coerce").dt.time 

# %%%% Cell 4
# --- unir los la carpeta de los csv 
# ==========================================
# 1️⃣ Columnas relevantes que vienen de los CSV
# ==========================================
COLUMNAS_CSV_ORIGEN = [
    "Ejecutivo",
    "ID_LEAD",
    "lead_id",
    "Mensaje Entrante",
    "Mensaje Saliente",
    "Fecha Entrante",
    "Hora Entrante",
    "Fecha Saliente",
    "Hora Saliente",
]

# ==========================================
# 2️⃣ Reemplazar 'hoy' / 'ayer' y normalizar fechas
# ==========================================

def _reemplazar_hoy_ayer_y_normalizar(
    df: pd.DataFrame,
    cols=("Fecha Entrante", "Fecha Saliente"),
    tz: str = "America/Lima"
) -> pd.DataFrame:
    """
    Para cada columna en cols:
      - 'hoy'/'Hoy'/... -> fecha actual (YYYY-MM-DD)
      - 'ayer'/'Ayer'/... -> fecha de ayer (YYYY-MM-DD)
      - 'YYYY-MM-DD' -> se mantiene
      - 'YYYY-MM-DD HH:MM:SS' -> se recorta a 'YYYY-MM-DD'
      - 'DD/MM/YYYY' -> se convierte a 'YYYY-MM-DD'
    Cualquier otra cosa rara -> NaN.
    """

    hoy = pd.Timestamp.now(tz=tz).normalize()
    ayer = hoy - pd.Timedelta(days=1)

    for col in cols:
        if col not in df.columns:
            continue

        # Serie como string, sin espacios
        s = df[col].astype(str).str.strip()
        lower = s.str.lower()

        # Mapear hoy/ayer
        s = s.mask(lower == "hoy",  hoy.strftime("%Y-%m-%d"))
        s = s.mask(lower == "ayer", ayer.strftime("%Y-%m-%d"))

        # Vacíos explícitos
        mask_empty = (
            (s == "") |
            lower.isin(["nan", "nat", "none", "null"])
        )

        # Patrones conocidos
        mask_ddmmyyyy = s.str.match(r"^\d{1,2}\/\d{1,2}\/\d{4}$", na=False)
        mask_iso_date = s.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
        mask_iso_dt   = s.str.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", na=False)

        parsed = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

        # DD/MM/YYYY - procesar primero
        if mask_ddmmyyyy.any():
            parsed.loc[mask_ddmmyyyy] = pd.to_datetime(
                s[mask_ddmmyyyy],
                format="%d/%m/%Y",
                errors="coerce",
            )

        # YYYY-MM-DD
        if mask_iso_date.any():
            parsed.loc[mask_iso_date] = pd.to_datetime(
                s[mask_iso_date],
                format="%Y-%m-%d",
                errors="coerce",
            )

        # YYYY-MM-DD HH:MM:SS
        if mask_iso_dt.any():
            parsed.loc[mask_iso_dt] = pd.to_datetime(
                s[mask_iso_dt],
                format="%Y-%m-%d %H:%M:%S",
                errors="coerce",
            )

        # DD/MM/YYYY
        if mask_ddmmyyyy.any():
            parsed.loc[mask_ddmmyyyy] = pd.to_datetime(
                s[mask_ddmmyyyy],
                format="%d/%m/%Y",
                errors="coerce",
            )

        # Vacíos reales
        parsed.loc[mask_empty] = pd.NaT

        # Guardar como YYYY-MM-DD (string) - manejar NaT correctamente
        df[col] = parsed.dt.strftime("%Y-%m-%d").where(pd.notna(parsed), pd.NaT)

    return df

# ==========================================
# 3️⃣ Alinear filas nuevas (CSV) al esquema del df_base
# ==========================================

def _alinear_a_base(df_origen: pd.DataFrame, base_cols: list) -> pd.DataFrame:
    """
    Construye un DataFrame con las MISMAS columnas que df_base:
    - Si una columna existe en df_origen, se copia.
    - Si no existe, se rellena con NaN.
    No agrega columnas nuevas fuera de base_cols.
    """
    out = pd.DataFrame(index=df_origen.index)

    for col in base_cols:
        if col in df_origen.columns:
            out[col] = df_origen[col]
        else:
            out[col] = pd.NA

    return out

# ==========================================
# 4️⃣ Procesar un CSV individual
# ==========================================

def _procesar_csv_unico(
    csv_path: Path,
    base_cols: list,
    tz: str = "America/Lima"
) -> Optional[pd.DataFrame]:
    """
    Lee un CSV y devuelve un DataFrame alineado a base_cols,
    usando SOLO las columnas relevantes de COLUMNAS_CSV_ORIGEN.
    """

    df_csv = pd.read_csv(csv_path)

    if df_csv.empty:
        print(f"[WARN] {csv_path.name}: CSV vacío, se omite.")
        return None

    # Conservar solo columnas relevantes
    cols_presentes = [c for c in COLUMNAS_CSV_ORIGEN if c in df_csv.columns]
    if not cols_presentes:
        print(f"[WARN] {csv_path.name}: no tiene columnas objetivo, se omite.")
        return None

    df_use = df_csv[cols_presentes].copy()

    # Crear ID_LEAD si falta y existe lead_id
    if "ID_LEAD" not in df_use.columns and "lead_id" in df_use.columns:
        df_use["ID_LEAD"] = df_use["lead_id"]

    # Normalizar fechas (incluye reemplazo de hoy/ayer)
    df_use = _reemplazar_hoy_ayer_y_normalizar(
        df_use,
        cols=("Fecha Entrante", "Fecha Saliente"),
        tz=tz,
    )

    # NO tocamos Hora Entrante / Hora Saliente

    # Alinear al esquema del df_base
    df_aligned = _alinear_a_base(df_use, base_cols)

    print(f"[INFO] {csv_path.name} procesado ({df_aligned.shape[0]} filas).")
    return df_aligned

# ==========================================
# 5️⃣ FUNCIÓN PRINCIPAL: unir df_base + CSVs
# ==========================================

def construir_df_general_desde_csv(
    carpetas: Iterable[str | Path],
    df_base: pd.DataFrame,
    extensiones: Tuple[str, ...] = (".csv",),
    tz: str = "America/Lima",
) -> pd.DataFrame:
    """
    Une:
      - df_base (histórico original COMPLETO, sin alterar columnas)
      - todas las filas nuevas de los CSV encontrados en 'carpetas'

    Reglas:
      - De los CSV solo se usan:
        Ejecutivo, ID_LEAD/lead_id, Mensaje Entrante, Mensaje Saliente,
        Fecha Entrante, Hora Entrante, Fecha Saliente, Hora Saliente.
      - 'hoy' / 'ayer' en fechas se reemplazan por fecha real,
        y todo se lleva a 'YYYY-MM-DD' sin perder info válida.
      - TODAS las columnas del df_base se mantienen.
      - Columnas no presentes en CSV quedan como NaN en filas nuevas
        (para que luego calcules tiempos, scores, segmentos, etc.).
    """

    if df_base is None or df_base.empty:
        raise ValueError("df_base (histórico) no puede ser None ni estar vacío.")

    base_cols = list(df_base.columns)
    dfs = [df_base.copy()]  # empezamos con tu histórico intacto

    for carpeta in map(Path, carpetas):
        if not carpeta.exists():
            print(f"[WARN] Carpeta no existe: {carpeta}")
            continue

        for ext in extensiones:
            for csv_path in carpeta.rglob(f"*{ext}"):
                try:
                    df_nuevo = _procesar_csv_unico(csv_path, base_cols, tz=tz)
                    if df_nuevo is not None:
                        dfs.append(df_nuevo)
                except Exception as e:
                    print(f"[ERROR] {csv_path.name}: {e}")

    # Si no hubo CSV válidos, devolver solo el histórico
    if len(dfs) == 1:
        return dfs[0]

    # Concatenar histórico + nuevos
    df_general = pd.concat(dfs, ignore_index=True, sort=False)

    # Orden opcional
    cols_orden = [
        c for c in [
            "Ejecutivo",
            "ID_LEAD",
            "Fecha Entrante",
            "Hora Entrante",
            "Fecha Saliente",
            "Hora Saliente",
        ]
        if c in df_general.columns
    ]

    if cols_orden:
        df_general = (
            df_general
            .sort_values(cols_orden, na_position="last")
            .reset_index(drop=True)
        )

    # Asegurar MISMO orden de columnas que df_base
    df_general = df_general[base_cols]

    return df_general



# %%%% Cell 5
# Llama a la función de unión pasando df_base=df 
df_general = construir_df_general_desde_csv(
    carpetas=[r"C:\Users\Lima - Rodrigo\Documents\ventas\files\output\12_18_ene"],
    df_base=df   # <- AQUÍ VA TU HISTÓRICO
)

# %%%% Cell 6
df_general[df_general['ID_LEAD']==4228]

# %%%% Cell 7
# df_fila=df_general[df_general["ID_LEAD"] == 19720141]
# # Usar .loc[] para asegurarse de que se modifican las columnas de df_fila directamente
# df_fila.loc[:, "Hora Entrante"] = df_fila["Hora Entrante"].apply(lambda x: pd.to_datetime(x, format="%H:%M:%S").time())
# df_fila.loc[:, "Hora Saliente"] = df_fila["Hora Saliente"].apply(lambda x: pd.to_datetime(x, format="%H:%M:%S").time())


# # Ver el resultado final
# print(df_fila[["Hora Entrante", "Hora Saliente"]])

# %%%% Cell 8
# --- primera inspeccion de los fromatos de FECHA despues del unido ---
def inspeccionar_formatos_fecha(df, col):
    s = df[col].dropna().astype(str).str.strip()

    patrones = {
        "YYYY-MM-DD":              r"^\d{4}-\d{2}-\d{2}$",
        "DD-MM-YYYY":              r"^\d{2}-\d{2}-\d{4}$",
        "DD/MM/YYYY":              r"^\d{2}/\d{2}/\d{4}$",
        "YYYY-MM-DD HH:MM:SS":     r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
        "DD/MM/YYYY HH:MM:SS":     r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$",
    }

    print(f"Revisando columna: {col}\nTotal valores (no nulos): {len(s)}\n")

    usados = []
    for nombre, pat in patrones.items():
        m = s.str.match(pat)
        count = m.sum()
        if count > 0:
            print(f"{nombre}: {count}")
            usados.append(m)

    if usados:
        usados_any = pd.concat(usados, axis=1).any(axis=1)
        raros = s[~usados_any]
    else:
        raros = s

    if len(raros) > 0:
        print(f"\n⚠ Valores raros / fuera de patrones: {len(raros)}")
        print("\n⚠ Otros formatos / valores raros (muestra):")
        print(raros.unique()[:20])
    else:
        print("\n✅ No se detectaron formatos raros fuera de los patrones definidos.")
inspeccionar_formatos_fecha(df_general, "Fecha Entrante")
inspeccionar_formatos_fecha(df_general, "Fecha Saliente")

# %%%% Cell 9
# --- normalizar las fechas despues del unido ---
def normalizar_columna_fecha(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Normaliza una columna de fechas a formato 'YYYY-MM-DD' (string),
    asumiendo SOLO estos formatos válidos de entrada:
      - 'YYYY-MM-DD'
      - 'YYYY-MM-DD HH:MM:SS'
      - 'DD/MM/YYYY'
    Todo lo demás:
      - Si es vacío o nulo -> NaN
      - No debería aparecer según tu diagnóstico.
    """

    if col not in df.columns:
        return df

    s = df[col].astype(str).str.strip()

    # Marcamos nulos/vacíos explícitos
    lower = s.str.lower()
    mask_empty = (
        (s == "") |
        lower.isin(["nan", "nat", "none", "null"])
    )

    # Patrones que ya sabes que existen
    mask_iso_date   = s.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
    mask_iso_dt     = s.str.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", na=False)
    mask_ddmmyyyy   = s.str.match(r"^\d{2}/\d{2}/\d{4}$", na=False)

    # Inicializamos como NaT
    parsed = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

    # YYYY-MM-DD
    if mask_iso_date.any():
        parsed.loc[mask_iso_date] = pd.to_datetime(
            s[mask_iso_date],
            format="%Y-%m-%d",
            errors="coerce"
        )

    # YYYY-MM-DD HH:MM:SS
    if mask_iso_dt.any():
        parsed.loc[mask_iso_dt] = pd.to_datetime(
            s[mask_iso_dt],
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce"
        )

    # DD/MM/YYYY
    if mask_ddmmyyyy.any():
        parsed.loc[mask_ddmmyyyy] = pd.to_datetime(
            s[mask_ddmmyyyy],
            format="%d/%m/%Y",
            errors="coerce"
        )

    # Vacíos reales a NaT
    parsed.loc[mask_empty] = pd.NaT

    # Resultado final como 'YYYY-MM-DD'
    df[col] = parsed.dt.strftime("%Y-%m-%d")

    return df
df_general = normalizar_columna_fecha(df_general, "Fecha Entrante")
df_general = normalizar_columna_fecha(df_general, "Fecha Saliente")
# %%%% Cell 10
df_general[df_general['ID_LEAD']==4228]
# %%%% Cell 11
# --- hacer segunda inspeccion ---

def inspeccionar_formatos_fecha(df, col):
    s = df[col].dropna().astype(str).str.strip()

    patrones = {
        "YYYY-MM-DD":              r"^\d{4}-\d{2}-\d{2}$",
        "DD-MM-YYYY":              r"^\d{2}-\d{2}-\d{4}$",
        "DD/MM/YYYY":              r"^\d{2}/\d{2}/\d{4}$",
        "YYYY-MM-DD HH:MM:SS":     r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
        "DD/MM/YYYY HH:MM:SS":     r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$",
    }

    print(f"Revisando columna: {col}\nTotal valores (no nulos): {len(s)}\n")

    usados = []
    for nombre, pat in patrones.items():
        m = s.str.match(pat)
        count = m.sum()
        if count > 0:
            print(f"{nombre}: {count}")
            usados.append(m)

    if usados:
        usados_any = pd.concat(usados, axis=1).any(axis=1)
        raros = s[~usados_any]
    else:
        raros = s

    if len(raros) > 0:
        print(f"\n⚠ Valores raros / fuera de patrones: {len(raros)}")
        print("\n⚠ Otros formatos / valores raros (muestra):")
        print(raros.unique()[:20])
    else:
        print("\n✅ No se detectaron formatos raros fuera de los patrones definidos.")
inspeccionar_formatos_fecha(df_general, "Fecha Entrante")
inspeccionar_formatos_fecha(df_general, "Fecha Saliente")

# %%%% Cell 12
# --- eliminar duplicados ---
df_general = df_general.drop_duplicates(subset=["ID_LEAD"], keep="first").reset_index(drop=True)

# %%%% Cell 14
# --- elimna celdas que no tengan id_lead ---
df_general = df_general.dropna(subset=["ID_LEAD"]).reset_index(drop=True)

# %%%% Cell 16
# --- dar formato a horas despues de la union ---
def normalizar_hora_col(serie):
    s = serie.astype(str).str.strip()
    lower = s.str.lower()

    # marcar vacíos
    mask_empty = (
        (s == "") |
        lower.isin(["nan", "nat", "none", "null"])
    )

    # 1) intentar HH:MM:SS.mmmmmm (con milisegundos)
    parsed = pd.to_datetime(s, format="%H:%M:%S.%f", errors="coerce")
    
    # 2) donde falló, intentar HH:MM:SS (sin milisegundos)
    mask_fail = parsed.isna() & ~mask_empty
    if mask_fail.any():
        parsed2 = pd.to_datetime(s[mask_fail], format="%H:%M:%S", errors="coerce")
        parsed.loc[mask_fail] = parsed2

    # 3) donde sigue fallando, intentar HH:MM
    mask_fail2 = parsed.isna() & ~mask_empty
    if mask_fail2.any():
        parsed3 = pd.to_datetime(s[mask_fail2], format="%H:%M", errors="coerce")
        parsed.loc[mask_fail2] = parsed3

    # 4) vacíos reales
    parsed.loc[mask_empty] = pd.NaT

    # devolver como HH:MM:SS (sin milisegundos)
    return parsed.dt.strftime("%H:%M:%S")

df_general["Hora Entrante"] = normalizar_hora_col(df_general["Hora Entrante"])
df_general["Hora Saliente"] = normalizar_hora_col(df_general["Hora Saliente"])
# %%%% Cell 6
df_general[df_general['ID_LEAD']==4228]

# %%%% Cell 15
# --- verificar fecha ---
# Convierte cada columna desde SI MISMA, en el MISMO df
df_general["Fecha Entrante"] = pd.to_datetime(df_general["Fecha Entrante"], errors="coerce")
df_general["Fecha Saliente"] = pd.to_datetime(df_general["Fecha Saliente"], errors="coerce")

# Ahora sí, máximo real (ignorando NaT)
print(df_general["Fecha Entrante"].max())
print(df_general["Fecha Saliente"].max())

# %%%% Cell 16
# --- agregar tiempo de respuesta min ---

def calcular_tiempo_respuesta_hhmmss_nan(
    df,
    col_fecha_in="Fecha Entrante",
    col_hora_in="Hora Entrante",
    col_fecha_out="Fecha Saliente",
    col_hora_out="Hora Saliente",
    out_col="Tiempo Respuesta (min)"
):
    """
    Rellena out_col (HH:MM:SS) solo cuando:
      - out_col está NaN
      - fecha+hora de entrada y salida son válidas
    Si falta fecha/hora de salida -> deja np.nan.
    No sobrescribe valores ya existentes.
    Usa np.nan para que se muestre 'NaN' (no '<NA>').
    """
    df = df.copy()

    # Asegurar existencia y tipo 'object' (para mezclar strings con np.nan)
    if out_col not in df.columns:
        df[out_col] = np.nan
    else:
        # Forzar dtype object y convertir cualquier <NA> a np.nan
        df[out_col] = df[out_col].astype(object)
        df.loc[df[out_col].isna(), out_col] = np.nan

    # Solo calcular donde la celda destino está NaN o es cadena vacía
    mask_target = df[out_col].isna() | (df[out_col].astype(str).str.strip() == "")

    # Requiere fecha/hora de SALIDA presentes
    mask_salida = df[col_fecha_out].notna() & df[col_hora_out].notna()
    mask = mask_target & mask_salida
    if not mask.any():
        return df

    # Parsear datetimes solo en filas objetivo
    entrada = pd.to_datetime(
        df.loc[mask, col_fecha_in].astype(str) + " " + df.loc[mask, col_hora_in].astype(str),
        errors="coerce"
    )
    salida = pd.to_datetime(
        df.loc[mask, col_fecha_out].astype(str) + " " + df.loc[mask, col_hora_out].astype(str),
        errors="coerce"
    )

    # Válidas y no negativas
    valid = entrada.notna() & salida.notna() & (salida >= entrada)
    if valid.any():
        delta = (salida[valid] - entrada[valid]).dt.round("s")
        comp = delta.dt.components  # days, hours, minutes, seconds

        total_hours = (comp["days"] * 24 + comp["hours"]).astype(int)
        hh = total_hours.astype(str).str.zfill(2)
        mm = comp["minutes"].astype(int).astype(str).str.zfill(2)
        ss = comp["seconds"].astype(int).astype(str).str.zfill(2)
        hhmmss = (hh + ":" + mm + ":" + ss)

        df.loc[delta.index, out_col] = hhmmss

    # Asegurar que faltantes queden exactamente como np.nan (se verá 'NaN')
    df.loc[df[out_col].isna(), out_col] = np.nan
    # Mantener dtype 'object' (NO convertir a 'string', porque eso vuelve a mostrar <NA>)
    return df

# %%%% Cell 17
# --- aplicar la funcion ---
df_general = calcular_tiempo_respuesta_hhmmss_nan(
    df_general,
    col_fecha_in="Fecha Entrante",
    col_hora_in="Hora Entrante",
    col_fecha_out="Fecha Saliente",
    col_hora_out="Hora Saliente",
    out_col="Tiempo Respuesta (min)"
)

# %%%% Cell 18
df_general[df_general['ID_LEAD']==4228]

# %%%% Cell 19
# --- Calcular score tiempo respuesta parte 1 ---
def calcular_score_tiempo_respuesta(df):
    # Copia del DataFrame para no modificar el original
    df = df.copy()


    # Iterar sobre cada fila para realizar los cálculos
    for idx, row in df.iterrows():
        # Si "Score Tiempo Respuesta" ya tiene valor, continuar
        #if pd.notna(row["Score Tiempo Respuesta"]):
            #continue

        # Verificar si "Fecha Saliente" y "Hora Saliente" son mayores o iguales que "Fecha Entrante" y "Hora Entrante"
        if pd.notna(row["Fecha Saliente"]) and pd.notna(row["Hora Saliente"]) and pd.notna(row["Fecha Entrante"]) and pd.notna(row["Hora Entrante"]):
            fecha_hora_salida = pd.to_datetime(f"{row['Fecha Saliente']} {row['Hora Saliente']}", errors='coerce')
            fecha_hora_entrada = pd.to_datetime(f"{row['Fecha Entrante']} {row['Hora Entrante']}", errors='coerce')
            
            # Comprobar si la fecha y hora de salida son mayores o iguales a la de entrada
            if fecha_hora_salida >= fecha_hora_entrada:
                # Obtener el tiempo de respuesta en formato HH:MM:SS
                tiempo_respuesta = row["Tiempo Respuesta (min)"]

                # Asegurarnos de que el valor esté en formato HH:MM:SS
                if isinstance(tiempo_respuesta, str):  # Si es un string en formato HH:MM:SS
                    try:
                        horas, minutos, segundos = map(int, tiempo_respuesta.split(":"))
                        tiempo_respuesta_segundos = horas * 3600 + minutos * 60 + segundos  # Convertir a segundos
                    except ValueError:
                        # Si el valor no tiene el formato esperado, lo dejamos tal cual
                        continue  # Ignorar esta fila y seguir con la siguiente
                else:
                    tiempo_respuesta_segundos = np.nan  # Si no es un string válido, dejar como NaN

                # Solo aplicar la fórmula si tenemos un valor válido de tiempo_respuesta_segundos
                if pd.notna(tiempo_respuesta_segundos):
                    # Aplicar la fórmula de Excel en base al tiempo en segundos
                    if abs(tiempo_respuesta_segundos) < 60:  # ⚙️ Automático (menos de 1 minuto)
                        df.at[idx, "Score Tiempo Respuesta"] = "⚙️ Automático"
                    elif tiempo_respuesta_segundos <= 300:  # 🟢 Excelente (hasta 5 minutos)
                        df.at[idx, "Score Tiempo Respuesta"] = "🟢 Excelente"
                    elif tiempo_respuesta_segundos <= 900:  # 🟡 Bueno (hasta 15 minutos)
                        df.at[idx, "Score Tiempo Respuesta"] = "🟡 Bueno"
                    elif tiempo_respuesta_segundos <= 3600:  # 🟠 Regular (hasta 60 minutos)
                        df.at[idx, "Score Tiempo Respuesta"] = "🟠 Regular"
                    elif tiempo_respuesta_segundos <= 86400:  # 🔴 Lento (hasta 1440 minutos = 24 horas)
                        df.at[idx, "Score Tiempo Respuesta"] = "🔴 Lento"
                    else:  # ⚫ Muy Lento (más de 24 horas)
                        df.at[idx, "Score Tiempo Respuesta"] = "⚫ Muy Lento"
    return df

# %%%% Cell 20
# --- Calcular score tiempo respuesta parte 2 ---
def calcular_score_tiempo_respuesta_pt2(df):
    out = df.copy()

    col_score = "Score Tiempo Respuesta"
    # Si no existe la columna, créala; si existe, NO la resetees
    if col_score not in out.columns:
        out[col_score] = np.nan

    # Filas a rellenar (solo donde no hay score aún)
    m_target = out[col_score].isna()

    # Construir datetimes de entrada/salida (tolerante a string/time/NaN)
    entrada_dt = pd.to_datetime(
        out["Fecha Entrante"].astype(str).str.strip() + " " + out["Hora Entrante"].astype(str).str.strip(),
        errors="coerce"
    )
    salida_dt = pd.to_datetime(
        out["Fecha Saliente"].astype(str).str.strip() + " " + out["Hora Saliente"].astype(str).str.strip(),
        errors="coerce"
    )

    # ⚠️ Outbound: salida < entrada (solo donde falta score y ambos datetimes válidos)
    m_outbound = m_target & salida_dt.notna() & entrada_dt.notna() & (salida_dt < entrada_dt)
    out.loc[m_outbound, col_score] = "⚠️ Outbound"

    # ❌ No respondido: falta fecha/hora de salida pero sí hay fecha/hora de entrada
    m_noresp = (
        m_target
        & (out["Fecha Saliente"].isna() | out["Hora Saliente"].isna())
        & out["Fecha Entrante"].notna()
        & out["Hora Entrante"].notna()
    )
    out.loc[m_noresp, col_score] = "❌ No respondido"

    # Todo lo demás queda tal cual (incluye casos raros: se dejan en NaN)
    return out

# %%%% Cell 21
# --- aplicación de la función pt1 ---
df_score_pt1 = calcular_score_tiempo_respuesta(df_general)
#--- aplicacion de la funcion pt2 ---
df_score_pt2 = calcular_score_tiempo_respuesta_pt2(df_score_pt1)

# %%%% Cell 18
df_score_pt2[df_score_pt2['ID_LEAD']==4228]

# %%%% Cell 23
# --- Comprobar el resultado ---
# Cambiar la configuración de pandas para mostrar más columnas en horizontal
pd.set_option('display.max_columns', None)  # Muestra todas las columnas
pd.set_option('display.width', 1000)        # Ajusta el ancho para que no corte las columnas
pd.set_option('display.max_colwidth', None) # Muestra el contenido completo de cada celda
# Ordenar el DataFrame por 'Fecha Saliente' de mayor a menor (más recientes primero)
df_sorted = df_score_pt2.sort_values(by="Fecha Entrante", ascending=False)

# Imprimir las primeras filas de las fechas más recientes
print(df_sorted.head(40))

# %%%% Cell 24
# --- completar segmento horario entrada ---


def calcular_segmento_horario_entrada(df):
    out = df.copy()

    col_segmento = "Segmento Horario Entrada"
    col_hora = "Hora Entrante"

    # Si no existe la columna, la creamos
    if col_segmento not in out.columns:
        out[col_segmento] = np.nan

    # Solo procesamos las filas donde está vacía
    mask_target = out[col_segmento].isna() & out[col_hora].notna()

    for idx, hora_str in out.loc[mask_target, col_hora].items():
        try:
            # Convertir a datetime.time si es string
            if isinstance(hora_str, str):
                hora = datetime.strptime(hora_str.strip(), "%H:%M:%S").time()
            else:
                hora = hora_str

            h = hora.hour  # extraemos la hora en entero

            # Asignar según las reglas de tu fórmula
            if h < 6:
                out.at[idx, col_segmento] = "🌙 Madrugada"
            elif h < 9:
                out.at[idx, col_segmento] = "🌤 Mañana no laborable"
            elif h < 13:
                out.at[idx, col_segmento] = "☀️ Mañana laborable"
            elif h < 18:
                out.at[idx, col_segmento] = "🌇 Tarde"
            elif h < 23:
                out.at[idx, col_segmento] = "🌆 Noche"
            else:
                out.at[idx, col_segmento] = "🌒 Noche tarde"

        except Exception:
            # Si la hora no tiene formato válido, dejar como NaN
            out.at[idx, col_segmento] = np.nan

    # Si después de todo sigue vacío, poner “❌ No registrado”
    out[col_segmento] = out[col_segmento].fillna("❌ No registrado")

    return out

# %%%% Cell 25
# --- aplicar funcion ---
df = calcular_segmento_horario_entrada(df_score_pt2)

# %%%% Cell 18
df[df['ID_LEAD']==4228]

# %%%% Cell 27
# --- verificar ---
# Cambiar la configuración de pandas para mostrar más columnas en horizontal
pd.set_option('display.max_columns', None)  # Muestra todas las columnas
pd.set_option('display.width', 1000)        # Ajusta el ancho para que no corte las columnas
pd.set_option('display.max_colwidth', None) # Muestra el contenido completo de cada celda
# Ordenar el DataFrame por 'Fecha Saliente' de mayor a menor (más recientes primero)
df_sorted = df.sort_values(by="Fecha Saliente", ascending=False)

# Imprimir las primeras filas de las fechas más recientes
print(df_sorted.head(40))

# %%%% Cell 28
# cambiar el nombre de omar a eduardo
df.loc[df["Ejecutivo"] == "Omar", "Ejecutivo"] = "Eduardo"
 

# %%%% Cell 29
# --- exportar y reemplazar el ultimo df a csv ---

ruta_salida = r"C:\Users\Lima - Rodrigo\Documents\ventas\files\input\nuevo_csv.csv"
df.to_csv(ruta_salida, index=False, encoding='utf-8-sig')
print(f"✅ Archivo exportado correctamente a:\n{ruta_salida}")

# %%%% Cell 30
#df=pd.read_csv(r"C:\Users\Lima - Rodrigo\Documents\3pro\kommo\historico\nuevo_csv.csv")

# %%%% Cell 31
#-----------------------------------------------------------------------------------------------
#                                     2da parte
#----------------------------------------------------------------------------------------------------------
# normalizar los nombres
mapeo = {
    "Carmen": "Karina",
    "JENNIFER": "Jennifer",
    "Omar": "Omar",
    "Rosmery": "RosmeryPapel",
    "ESTRELLA": "EstrellaCondori",
    "YAMELY": "Yamely",
    # agrega los que quieras...
}

# Configuración de turnos, manteniendo los turnos regulares
MAPA_TURNOS = {
    "mañana": ("09:00", "18:00"),
    "manana": ("09:00", "18:00"),  # por si viene sin tilde
    "tarde": ("14:00", "22:00"),
}

# Función para procesar las fechas
def _to_dt(x):
    """Devuelve Timestamp o NaT sin romper si hay strings raros."""
    return pd.to_datetime(x, errors="coerce")

# Normalización de texto
def _norm_txt(s):
    """Devuelve (original_normalizado, sin_acentos) en minúsculas."""
    if pd.isna(s):
        return "", ""
    s = str(s).strip().lower()
    s_noacc = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    return s, s_noacc


def parse_semana_expand(df):
    df = df.copy()
    df.columns = ["c0", "c1", "c2"][:len(df.columns)]

    rows = []
    inicio = fin = None

    for _, r in df.iterrows():
        c0 = r.get("c0", None)
        c1 = r.get("c1", None)
        c2 = r.get("c2", None)

        # ¿Cabecera semanal? (dos fechas válidas y c2 vacío)
        c0dt, c1dt = _to_dt(c0), _to_dt(c1)
        if pd.notna(c0dt) and pd.notna(c1dt) and (pd.isna(c2) or str(c2).strip() == ""):
            inicio = c0dt.normalize()
            fin = c1dt.normalize()
            continue

        # Si aún no hay semana activa, ignorar
        if inicio is None or fin is None:
            continue

        # Fila operador + turno
        operador_raw = None if pd.isna(c0) else str(c0).strip()
        if not operador_raw:
            continue

        # mapeo nombres
        operador = mapeo.get(operador_raw, operador_raw)

        t_raw, t_noacc = _norm_txt(c2)
        if not t_raw:
            continue

        # Detectar clave de turno
        if "tarde" in t_noacc:
            clave = "tarde"
        elif "manana" in t_noacc or "mañana" in t_raw:
            clave = "mañana"
        else:
            continue

        operador_norm = operador.strip().lower()


        # Expansión: generar una fila por cada fecha del rango [inicio, fin]
        for d in pd.date_range(inicio, fin, freq="D"):
            wd = d.weekday()  # 0=lun ... 5=sab, 6=dom

            # 🚫 No generar ninguna fila para DOMINGO
            if wd == 6:
                continue

            d_str = d.date().isoformat()  # 'YYYY-MM-DD'
                        # ===================== EXCEPCIONES GLOBALES =====================
            # 31: no se cuenta nada (no se generan filas)
            if d_str == "2025-12-31":
                continue

            # 30: desde las 13:00 nadie trabaja (recortar turnos)
            corte_global = None
            if d_str == "2025-12-30":
                corte_global = pd.to_datetime(f"{d_str} 13:00")
            # ================================================================

            # ===================== ASIGNACIÓN DE HORARIOS =====================
            
            # 1️⃣ EXCEPCIONES ESPECIALES (tienen prioridad)
            
            # Jennifer: días excluidos
            if operador_norm == "jennifer":
                if d_str in ("2025-11-10", "2025-11-15","2025-11-17"):
                    continue  # ❌ No trabaja estos días
                
                # Jennifer: horario especial 2025-11-14
                if d_str == "2025-11-14":
                    hora_ini = "09:00"
                    hora_fin = "16:00"
                else:
                    # Jennifer: días normales usan MAPA_TURNOS
                    hora_ini, hora_fin = MAPA_TURNOS.get(clave, ("09:00", "18:00"))
            
            # Yamely: horario especial 2025-11-22
            elif operador_norm == "yamely" and d_str == "2025-11-22":
                hora_ini = "09:00"
                hora_fin = "13:00"
            
            # Karina: lunes-viernes horario especial
            elif operador_norm == "karina" and wd <= 4:  # 0..4 = lun–vie
                hora_ini = "08:00"
                hora_fin = "15:00"
            
            # 2️⃣ REGLAS POR DÍA DE SEMANA
            
            # Sábado: reglas especiales para todos
            elif wd == 5:  # sábado
                if clave == "mañana":
                    hora_ini, hora_fin = "09:00", "13:00"
                elif clave == "tarde":
                    hora_ini, hora_fin = "18:00", "22:00"
                else:
                    hora_ini, hora_fin = MAPA_TURNOS[clave]
            
            # Resto de días: turnos normales según MAPA_TURNOS
            else:
                hora_ini, hora_fin = MAPA_TURNOS[clave]

            # 3️⃣ CORTE GLOBAL 2025-12-30
            if corte_global is not None:
                if ini_dt >= corte_global:
                    continue  # Si empieza después de las 13:00, no cuenta
                if fin_dt > corte_global:
                    fin_dt = corte_global
                    hora_fin = "13:00"

            # 4️⃣ CREAR FILA
            ini_dt = pd.to_datetime(f"{d_str} {hora_ini}")
            fin_dt = pd.to_datetime(f"{d_str} {hora_fin}")

            rows.append(
                {
                    "fecha": d.normalize(),
                    "operador": operador,
                    "turno": clave,
                    "hora_inicio": hora_ini,
                    "hora_fin": hora_fin,
                    "inicio_dt": ini_dt,
                    "fin_dt": fin_dt,
                }
            )

    out = (
        pd.DataFrame(rows)
        .drop_duplicates(subset=["fecha", "operador", "inicio_dt", "fin_dt"])
        .sort_values(["fecha", "inicio_dt", "operador"])
        .reset_index(drop=True)
    )

    return out


# ===================== EJEMPLO: leer tu Excel y parsear =====================

df_raw = pd.read_excel(
    r"C:\Users\Lima - Rodrigo\Documents\3pro\kommo\horario\horario_limpio.xlsx",
    header=None
)

tabla = parse_semana_expand(df_raw)
tabla = tabla.rename(columns={"operador": "Ejecutivo"})
print(tabla.head(12))

# %%%% Cell 32
# --- arreglar formato de fechas ---
# Convierte cada columna desde SI MISMA, en el MISMO df
tabla["fecha"] = pd.to_datetime(tabla["fecha"], errors="coerce")


# Ahora sí, máximo real (ignorando NaT)
tabla["fecha"].max()


#print(tabla[tabla['fecha']=='2025-11-22'])

# %%%% Cell 33
#--- cruzar datos --- 
# --- 1) Índice de origen para volver a tu df luego
tmp_df = df.reset_index().rename(columns={"index": "_orig"}).copy()

# --- 2) Temporales para cruce
tmp_df["_dt"]    = pd.to_datetime(tmp_df["Fecha Entrante"].astype(str) + " " + tmp_df["Hora Entrante"].astype(str),
                                  errors="coerce")
tmp_df["_fecha"] = pd.to_datetime(tmp_df["Fecha Entrante"], errors="coerce").dt.normalize()
tmp_df["_Ejecutivo"] = tmp_df["Ejecutivo"]

# --- 3) Temporales de tabla (horarios)
tmp_tabla = tabla.copy()
# Detectar nombre de la col del ejecutivo en tabla sin renombrar tu df original
exec_col = "Ejecutivo" if "Ejecutivo" in tmp_tabla.columns else "operador"
tmp_tabla["_Ejecutivo"] = tmp_tabla[exec_col]
tmp_tabla["_fecha"] = pd.to_datetime(tmp_tabla["fecha"], errors="coerce").dt.normalize()

# (Opcional pero recomendado) Si hay duplicados de horario por día/ejecutivo y te da igual el “hueco” entre turnos,
# colapsa a una sola ventana amplia (mínimo inicio, máximo fin). Si quieres respetar huecos, omite este bloque.
tmp_tabla = (tmp_tabla
             .groupby(["_Ejecutivo", "_fecha"], as_index=False)
             .agg(inicio_dt=("inicio_dt", "min"), fin_dt=("fin_dt", "max")))

# --- 4) Merge (puede ser many-to-one; si queda many-to-many, igual lo resolvemos por _orig)
merged = tmp_df.merge(
    tmp_tabla[["_Ejecutivo", "_fecha", "inicio_dt", "fin_dt"]],
    on=["_Ejecutivo", "_fecha"],
    how="left"
)

# --- 5) Condición por fila del MERGE
hit = ((merged["_dt"] >= merged["inicio_dt"]) & (merged["_dt"] <= merged["fin_dt"])).fillna(False)

# --- 6) Reducir a una máscara por lead original (si CUALQUIERA de las filas matchea, es True)
mask_por_orig = merged.assign(hit=hit).groupby("_orig")["hit"].any()

# --- 7) Filtrar devolviendo SOLO las columnas originales de df (mismo esquema)
df_en_horario = df.loc[mask_por_orig.values].copy()
# (si quieres revisar los fuera de horario)
# df_fuera_horario = df.loc[~mask_por_orig.values].copy()

# %%%% Cell 34
# --- Guarda el CSV con leads dentro del horario laboral sin índice ---
out_path=r"C:\Users\Lima - Rodrigo\Documents\3pro\kommo\horario\csv_horario.csv"
df_en_horario.to_csv(out_path, index=False, sep=",", encoding="utf-8-sig")
print("OK ->", out_path)

# %%%% Cell 35
df_en_horario=pd.read_csv(r"C:\Users\Lima - Rodrigo\Documents\3pro\kommo\horario\csv_horario.csv")

# %%%% Cell 36
#df_en_horario=pd.read_csv(r"C:\Users\Lima - Rodrigo\Documents\3pro\kommo\horario\csv_horario.csv")
# pedidos por ejecutivo
# Filtro por ejecutiva y rango de fechas (incluye ambos días)
mask = (
    (df_en_horario['Ejecutivo'] == 'Jennifer') &
    (df_en_horario['Fecha Entrante'].between('2026-01-12', '2026-01-18'))
)

df_operador = df_en_horario.loc[mask]

# Exportar a Excel
ruta= r"C:\Users\Lima - Rodrigo\Documents\3pro\kommo\pedidos\19_jan\Jennifer.xlsx"
df_operador.to_excel(ruta, index=False)

# %%%% Cell 37
inicio = '2025-11-17'
fin    = '2025-11-18'

df_filtrado = df_en_horario[
    (df_en_horario['Fecha Entrante'] >= inicio) &
    (df_en_horario['Fecha Entrante'] <= fin)
]

print(df_filtrado)

# %%%% Cell 38
df_en_horario[df_en_horario['ID_LEAD']==19803457]

# %%%% Cell 39
df_en_horario['Ejecutivo'].unique()

# %%%% Cell 40

