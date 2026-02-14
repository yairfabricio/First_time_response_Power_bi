import pandas as pd
import re
import os
from datetime import datetime
from pathlib import Path

# ===============================
# CONFIGURACIÓN DE CARPETAS
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = BASE_DIR / "files" / "input" / "wpp"
OUTPUT_DIR = BASE_DIR / "files" / "output" / datetime.now().strftime("%Y-%m-%d")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
INTERMEDIATE_DIR = BASE_DIR / "files" / "intermediate" / "wpp"
INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

# Autores que representan "mis mensajes" (owner) - se completan con el ejecutivo por CSV
OWNER_NAMES_BASE = {
    "Tú", "You", "Me",
    "Karina Evedove Asesora de viajes a Peru ILLAPA CULTURAS ANDINAS",
    "Ros Papel - Agente de viajes",
    "Eduardo/Asesor de Viajes a Perú",
    "Jennifer Formiga - Asesora de Viajes a Perú",
    "Estrella Condori",
    "Claribel Tarazona - Asesora de Viajes a Perú",
    "New Owner 1",
    "New Owner 2"
}

OWNER_NAMES_N = set()


def set_owner_names(ejecutivo: str):
    """Actualiza el set global de nombres del owner agregando el nombre del archivo."""
    global OWNER_NAMES_N
    owner_names = set(OWNER_NAMES_BASE)
    owner_names.add(ejecutivo)
    OWNER_NAMES_N = {norm_name(x) for x in owner_names}


# ===============================
# HELPERS
# ===============================
def norm_name(s: str) -> str:
    s = "" if s is None else str(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()

OWNER_NAMES_N = set()


# Regex tolerante: no exige fin de línea y permite texto extra luego del autor
META_RE = re.compile(
    r"""^\[
        (?P<hora>\d{1,2}:\d{2})
        \s*(?P<ampm>(?:a\.?\s?m\.?|p\.?\s?m\.?|am|pm))?
        \s*,\s*
        (?P<fecha>\d{1,2}/\d{1,2}/\d{4})
        \]\s*
        (?:(?P<autor>[^:]+):)?
        """,
    re.IGNORECASE | re.VERBOSE
)

def _normalize_spaces(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    # NBSP y narrow NBSP que aparecen en "p. m." a veces
    return s.replace("\u202f", " ").replace("\xa0", " ")

def _normalize_ampm(ampm: str) -> str:
    ampm = _normalize_spaces(ampm)
    ampm_clean = re.sub(r"\s+", "", ampm).lower()
    if ampm_clean in ("am", "a.m", "a.m."):
        return "AM"
    if ampm_clean in ("pm", "p.m", "p.m."):
        return "PM"
    return ""

def _parse_date_smart(fecha: str):
    """
    fecha viene como n1/n2/YYYY (ambigua).
    Regla:
      - si n1 > 12 => D/M
      - si n2 > 12 => M/D
      - si ambos <= 12 => asume D/M (WhatsApp ES)
    """
    if not fecha:
        return None
    try:
        n1, n2, y = fecha.split("/")
        a = int(n1); b = int(n2); y = int(y)
    except Exception:
        return None

    if a > 12:
        day, month = a, b
    elif b > 12:
        month, day = a, b
    else:
        day, month = a, b  # default D/M

    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return day, month, y

def parse_meta(meta: str):
    """
    Devuelve: (hora_24_str, autor, dt_real)
    """
    meta = _normalize_spaces(meta).strip()
    m = META_RE.match(meta)
    if not m:
        return None, None, None

    fecha_raw = (m.group("fecha") or "").strip()
    hhmm = (m.group("hora") or "").strip()
    ampm = _normalize_ampm(m.group("ampm") or "")
    autor = (m.group("autor") or "").strip() or None

    dmy = _parse_date_smart(fecha_raw)
    if dmy is None:
        return None, autor, None
    day, month, year = dmy

    # hora a 24h
    try:
        if ampm in ("AM", "PM"):
            t = pd.to_datetime(f"{hhmm} {ampm}", format="%I:%M %p", errors="coerce")
            if pd.isna(t):
                return None, autor, None
            hour = int(t.strftime("%H"))
            minute = int(t.strftime("%M"))
        else:
            hour, minute = map(int, hhmm.split(":"))

        dt_real = datetime(year, month, day, hour, minute, 0)
        hora_24 = f"{hour:02d}:{minute:02d}:00"
        return hora_24, autor, dt_real
    except Exception:
        return None, autor, None


def process_csv(csv_path: Path):
    """Procesa un CSV individual y genera salidas CSV + Parquets."""
    ejecutivo = csv_path.stem
    set_owner_names(ejecutivo)

    output_csv = OUTPUT_DIR / f"{ejecutivo}.csv"

    print(f"\n📥 Cargando CSV: {csv_path}")
    df = pd.read_csv(
        csv_path,
        dtype=str,
        keep_default_na=False,
        engine="python"
    )

    for c in ["contact", "meta", "text"]:
        if c not in df.columns:
            raise ValueError(f"{csv_path.name}: falta la columna '{c}'. Encontradas: {list(df.columns)}")

    df["contact"] = df["contact"].astype(str).str.strip()
    df["meta"]    = df["meta"].astype(str).str.strip()
    df["text"]    = df["text"].astype(str).str.strip()

    print("🔧 Parseando meta -> DT...")
    parsed = df["meta"].apply(parse_meta)
    df["Hora"]  = parsed.apply(lambda x: x[0])
    df["Autor"] = parsed.apply(lambda x: x[1])
    df["DT"]    = parsed.apply(lambda x: x[2])

    df = df[df["DT"].notna()].copy()
    print(f"📊 Filas con DT válido: {len(df)}")

    df["Fecha"] = df["DT"].dt.strftime("%d/%m/%Y")
    df["Hora"]  = df["DT"].dt.strftime("%H:%M:%S")

    print("🔄 Procesando conversaciones...")
    rows = []

    for contact, g in df.groupby("contact", sort=False):
        g = g.sort_values("DT").reset_index(drop=True)

        welcome_msg = "¡Hola! ¿Cómo podemos ayudarte?"
        if len(g) > 0 and g.loc[0, "text"] == welcome_msg:
            g = g.iloc[1:].reset_index(drop=True)
            if len(g) == 0:
                continue

        first_dt = g["DT"].iloc[0]
        g_first = g[g["DT"] == first_dt].copy()

        in_idx = None
        for idx, r in g_first.iterrows():
            autor = r["Autor"]
            if autor and norm_name(autor) not in OWNER_NAMES_N:
                in_idx = idx
                break

        if in_idx is not None:
            fecha_ent = g.loc[in_idx, "Fecha"]
            hora_ent  = g.loc[in_idx, "Hora"]
            dt_ent    = g.loc[in_idx, "DT"]

            out_idx = None
            for j in range(len(g)):
                if g.loc[j, "DT"] < dt_ent:
                    continue
                autor = g.loc[j, "Autor"]
                if autor and norm_name(autor) in OWNER_NAMES_N:
                    out_idx = j
                    break

            if out_idx is None:
                rows.append({
                    "Ejecutivo": ejecutivo,
                    "ID_LEAD": contact,
                    "Mensaje Entrante": "SI",
                    "Mensaje Saliente": "NO",
                    "Fecha Entrante": fecha_ent,
                    "Hora Entrante": hora_ent,
                    "Fecha Saliente": None,
                    "Hora Saliente": None,
                })
            else:
                rows.append({
                    "Ejecutivo": ejecutivo,
                    "ID_LEAD": contact,
                    "Mensaje Entrante": "SI",
                    "Mensaje Saliente": "SI",
                    "Fecha Entrante": fecha_ent,
                    "Hora Entrante": hora_ent,
                    "Fecha Saliente": g.loc[out_idx, "Fecha"],
                    "Hora Saliente": g.loc[out_idx, "Hora"],
                })
        else:
            rows.append({
                "Ejecutivo": ejecutivo,
                "ID_LEAD": contact,
                "Mensaje Entrante": "NO",
                "Mensaje Saliente": "SI",
                "Fecha Entrante": None,
                "Hora Entrante": None,
                "Fecha Saliente": g.loc[0, "Fecha"],
                "Hora Saliente": g.loc[0, "Hora"],
            })

    out = pd.DataFrame(rows)

    out.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print("✅ CSV final generado:", output_csv)
    print("📊 Chats exportados:", len(out))
    print("📌 Entrante=SI:", int((out["Mensaje Entrante"] == "SI").sum()))
    print("📌 Entrante=NO:", int((out["Mensaje Entrante"] == "NO").sum()))

    def _tipo_mensaje(autor):
        if autor and norm_name(autor) in OWNER_NAMES_N:
            return "Saliente"
        return "Entrante"

    df_detallado = df.copy()
    df_detallado["Ejecutivo"] = ejecutivo
    df_detallado["ID_LEAD"] = df_detallado["contact"]
    df_detallado["ID_LEAD_CW"] = df_detallado["contact"]
    df_detallado["Tipo_Mensaje"] = df_detallado["Autor"].apply(_tipo_mensaje)
    df_detallado["Contenido_Mensaje"] = df_detallado["text"]
    df_detallado["Fecha_Hora"] = df_detallado["DT"]
    df_detallado = df_detallado.sort_values(["contact", "Fecha_Hora"])
    df_detallado["Secuencia"] = df_detallado.groupby("contact").cumcount() + 1
    df_detallado["ID_Mensaje"] = range(1, len(df_detallado) + 1)

    df_detallado = df_detallado[[
        "ID_Mensaje",
        "ID_LEAD",
        "ID_LEAD_CW",
        "Ejecutivo",
        "Fecha_Hora",
        "Tipo_Mensaje",
        "Contenido_Mensaje",
        "Secuencia"
    ]]

    mensajes_entrantes = df_detallado[df_detallado["Tipo_Mensaje"] == "Entrante"].groupby("ID_LEAD_CW").size()
    mensajes_salientes = df_detallado[df_detallado["Tipo_Mensaje"] == "Saliente"].groupby("ID_LEAD_CW").size()

    resumen = df_detallado.groupby(["ID_LEAD_CW", "ID_LEAD", "Ejecutivo"]).agg({
        "ID_Mensaje": "count",
        "Fecha_Hora": ["min", "max"]
    }).reset_index()

    resumen.columns = [
        "ID_LEAD_CW",
        "ID_LEAD",
        "Ejecutivo",
        "Total_Mensajes",
        "Primer_Mensaje",
        "Ultimo_Mensaje"
    ]

    resumen["Mensajes_Cliente"] = resumen["ID_LEAD_CW"].map(mensajes_entrantes).fillna(0).astype(int)
    resumen["Mensajes_Vendedor"] = resumen["ID_LEAD_CW"].map(mensajes_salientes).fillna(0).astype(int)

    def calcular_duracion(row):
        if pd.notna(row["Primer_Mensaje"]) and pd.notna(row["Ultimo_Mensaje"]):
            delta = row["Ultimo_Mensaje"] - row["Primer_Mensaje"]
            return round(delta.total_seconds() / 60, 2)
        return 0.0

    resumen["Duracion_Conversacion_Min"] = resumen.apply(calcular_duracion, axis=1)
    resumen["Ratio_Vendedor_Cliente"] = (
        resumen["Mensajes_Vendedor"] / resumen["Mensajes_Cliente"].replace(0, 1)
    ).round(2)

    parquet_detallado = INTERMEDIATE_DIR / f"{ejecutivo}_mensajes_whatsapp_powerbi.parquet"
    df_detallado.to_parquet(parquet_detallado, index=False)
    print("💾 Parquet detallado guardado en:", parquet_detallado)

    parquet_resumen = INTERMEDIATE_DIR / f"{ejecutivo}_resumen_whatsapp_powerbi.parquet"
    resumen.to_parquet(parquet_resumen, index=False)
    print("💾 Parquet resumen guardado en:", parquet_resumen)

    return {
        "ejecutivo": ejecutivo,
        "archivo": csv_path.name,
        "chats": len(out),
        "entrantes": int((out["Mensaje Entrante"] == "SI").sum()),
        "sin_entrante": int((out["Mensaje Entrante"] == "NO").sum())
    }


def discover_csv_files():
    return sorted(INPUT_DIR.glob("*.csv"))


def main():
    csv_files = discover_csv_files()
    if not csv_files:
        print(f"No se encontraron CSV en {INPUT_DIR}")
        return

    print(f"Se procesarán {len(csv_files)} archivo(s) desde {INPUT_DIR}")
    resultados = []
    for csv_path in csv_files:
        try:
            resultados.append(process_csv(csv_path))
        except Exception as exc:
            print(f"❌ Error procesando {csv_path.name}: {exc}")

    if resultados:
        print("\nResumen general:")
        for r in resultados:
            print(
                f"- {r['archivo']} -> chats: {r['chats']} | entrantes SI: {r['entrantes']} | entrantes NO: {r['sin_entrante']}"
            )
    else:
        print("No se generaron resultados.")


if __name__ == "__main__":
    main()
