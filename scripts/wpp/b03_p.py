import pandas as pd
import re
import os
from datetime import datetime

# ===============================
# CONFIG
# ===============================
INPUT_CSV = r"C:\Users\Lima - Rodrigo\Documents\ventas\files\input\wpp\RosmeryPapel.csv"
OUTPUT_DIR = r"C:\Users\Lima - Rodrigo\Documents\ventas\files\output\12_18_ene"
os.makedirs(OUTPUT_DIR, exist_ok=True)

base_name = os.path.splitext(os.path.basename(INPUT_CSV))[0]
EJECUTIVO = base_name
OUTPUT_CSV = os.path.join(OUTPUT_DIR, f"{EJECUTIVO}.csv")

# Autores que representan "mis mensajes" (owner)
OWNER_NAMES = {
    "Tú", "You", "Me",
    EJECUTIVO,
    "Karina Evedove Asesora de viajes a Peru ILLAPA CULTURAS ANDINAS",
    "Ros Papel - Agente de viajes",
    "Eduardo/Asesor de Viajes a Perú",
    "Jennifer Formiga - Asesora de Viajes a Perú",
    "Estrella Condori"
}

# ===============================
# HELPERS
# ===============================
def norm_name(s: str) -> str:
    s = "" if s is None else str(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()

OWNER_NAMES_N = {norm_name(x) for x in OWNER_NAMES}

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


# ===============================
# LOAD
# ===============================
print("📥 Cargando CSV original...")
df = pd.read_csv(
    INPUT_CSV,
    dtype=str,
    keep_default_na=False,
    engine="python"
)

for c in ["contact", "meta", "text"]:
    if c not in df.columns:
        raise ValueError(f"Falta la columna '{c}'. Encontradas: {list(df.columns)}")

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

# ===============================
# FORMAR CSV FINAL (1 fila por chat)
# Regla corregida para empates en el primer DT:
# - Tomar DT más antiguo del chat
# - Si en ese DT hay cliente (no-owner): Entrante ese, y Saliente = primer owner con DT > DT_entrante
# - Si no hay cliente en ese DT: Entrante=NO y Saliente=SI (primer mensaje)
# ===============================
print("🔄 Procesando conversaciones...")
rows = []

for contact, g in df.groupby("contact", sort=False):
    g = g.sort_values("DT").reset_index(drop=True)

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
            if g.loc[j, "DT"] <= dt_ent:
                continue
            autor = g.loc[j, "Autor"]
            if autor and norm_name(autor) in OWNER_NAMES_N:
                out_idx = j
                break

        if out_idx is None:
            rows.append({
                "Ejecutivo": EJECUTIVO,
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
                "Ejecutivo": EJECUTIVO,
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
            "Ejecutivo": EJECUTIVO,
            "ID_LEAD": contact,
            "Mensaje Entrante": "NO",
            "Mensaje Saliente": "SI",
            "Fecha Entrante": None,
            "Hora Entrante": None,
            "Fecha Saliente": g.loc[0, "Fecha"],
            "Hora Saliente": g.loc[0, "Hora"],
        })

out = pd.DataFrame(rows)

# ===============================
# EXPORT FINAL
# ===============================
out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print("✅ CSV final generado:", OUTPUT_CSV)
print("📊 Chats exportados:", len(out))
print("📌 Entrante=SI:", int((out["Mensaje Entrante"] == "SI").sum()))
print("📌 Entrante=NO:", int((out["Mensaje Entrante"] == "NO").sum()))
