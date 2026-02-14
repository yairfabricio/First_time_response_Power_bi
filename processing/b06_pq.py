import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_INTERMEDIATE = ROOT / "files" / "intermediate"
SOURCE_DIRS = [BASE_INTERMEDIATE / "cw", BASE_INTERMEDIATE / "wpp"]


def gather_parquet_paths(kind: str) -> list[Path]:
    """Return a list of parquet files for the requested kind."""
    collected: list[Path] = []
    keyword = "mensajes" if kind == "detalle" else "resumen"

    for source in SOURCE_DIRS:
        if not source.exists():
            continue
        for path in source.glob("*.parquet"):
            name = path.name.lower()
            if keyword in name:
                if kind == "detalle" and "resumen" in name:
                    continue
                collected.append(path)
    return collected


def combine_parquets(paths: list[Path], target: Path) -> None:
    """Concatenate parquet files and write to target."""
    if not paths:
        print(f"No parquet files found for {target.name}, skipping.")
        return

    dfs = []
    for p in paths:
        df = pd.read_parquet(p)
        for col in ("ID_LEAD", "ID_LEAD_CW"):
            if col in df.columns:
                df[col] = df[col].astype(str)
        dfs.append(df)
    combined = pd.concat(dfs, ignore_index=True, sort=False)
    combined.to_parquet(target, index=False)
    print(f"💾 Guardado consolidado: {target} ({len(combined):,} filas)")


def main() -> None:
    BASE_INTERMEDIATE.mkdir(parents=True, exist_ok=True)
    BASE_OUTPUT = ROOT / "files" / "output" / "parquet"
    BASE_OUTPUT.mkdir(parents=True, exist_ok=True)

    detalle_paths = gather_parquet_paths("detalle")
    resumen_paths = gather_parquet_paths("resumen")

    output_detalle = BASE_OUTPUT / "consolidated_mensajes.parquet"
    output_resumen = BASE_OUTPUT / "consolidated_resumen.parquet"

    combine_parquets(detalle_paths, output_detalle)
    combine_parquets(resumen_paths, output_resumen)


if __name__ == "__main__":
    main()
