# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import hashlib
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# 1) CARGA ROBUSTA DE LA BASE
# -----------------------------------------------------------------------------
# Prioridad:
#   1. Variable de entorno LIQUIDITY_BASE_PATH
#   2. Base_M.csv junto a este archivo
#   3. Ruta de red histórica
#
# Así el dashboard puede correr tanto en tu PC/carpeta local como en la red BBVA.

_THIS_DIR = Path(__file__).resolve().parent
_DATA_DIR = Path(os.getenv("DASHBOARD_DATA_DIR", str(_THIS_DIR / "data_files"))).expanduser()
_LOCAL_BASE = _DATA_DIR / "Base_M.csv"
_LEGACY_LOCAL_BASE = _THIS_DIR / "Base_M.csv"


def _resolve_base_path() -> Path:
    explicit = os.getenv("LIQUIDITY_BASE_PATH")
    candidates = ([Path(explicit).expanduser()] if explicit else []) + [
        _LOCAL_BASE, _LEGACY_LOCAL_BASE
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "No se encontró Base_M.csv. Rutas revisadas: "
        + ", ".join(str(p) for p in candidates)
        + ". Define LIQUIDITY_BASE_PATH o DASHBOARD_DATA_DIR."
    )


# -----------------------------------------------------------------------------
# 1b) LECTURA SEGURA DE BASES GRANDES EN RUTAS SMB/UNC
# -----------------------------------------------------------------------------
# Pandas puede emitir OSError [Errno 22] al leer directamente un CSV grande
# sobre un recurso de red. Se descarga una copia temporal LOCAL, que se reutiliza
# si el origen no ha cambiado. NO se modifica Base_M.csv original.
# Si la copia falla o el origen cambia a mitad de lectura, se detiene con un
# mensaje claro (nunca utiliza una copia desactualizada en silencio).


def _base_csv_local_cache(source: Path, attempts: int = 3) -> Path:
    source = Path(source)
    cache_root = Path(
        os.environ.get("LIQUIDITY_CACHE_DIR")
        or (Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
            / "BBVA_MISU" / "LiquidityCache")
    )
    cache_root.mkdir(parents=True, exist_ok=True)

    # Distintas rutas de origen deben tener distintos ficheros de cache.
    key = hashlib.sha256(str(source).casefold().encode("utf-8")).hexdigest()[:12]
    cache_csv = cache_root / f"Base_M_{key}.csv"
    cache_meta = cache_root / f"Base_M_{key}.json"

    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            start = source.stat()
            fingerprint = {
                "source": str(source),
                "size": int(start.st_size),
                "mtime_ns": int(start.st_mtime_ns),
            }

            # Reutilizar SOLO si coincide el origen, su tamano y modificacion.
            if cache_csv.is_file() and cache_meta.is_file():
                try:
                    cached = json.loads(cache_meta.read_text(encoding="utf-8"))
                    if (cached == fingerprint
                            and cache_csv.stat().st_size == start.st_size):
                        print(f"[MISU] Base_M.csv local (cache vigente): {cache_csv}")
                        return cache_csv
                except (OSError, ValueError, TypeError):
                    pass

            print(f"[MISU] Copiando Base_M.csv desde la red a cache local "
                  f"(intento {attempt}/{attempts})...")
            tmp_csv = cache_root / f".Base_M_{key}_{os.getpid()}.part"
            try:
                with source.open("rb") as src, tmp_csv.open("wb") as dst:
                    shutil.copyfileobj(src, dst, length=4 * 1024 * 1024)

                end = source.stat()
                if (start.st_size != end.st_size
                        or start.st_mtime_ns != end.st_mtime_ns
                        or tmp_csv.stat().st_size != start.st_size):
                    raise OSError("Base_M.csv cambio mientras se copiaba; "
                                  "espera a que termine su actualizacion")

                os.replace(tmp_csv, cache_csv)
                tmp_meta = cache_meta.with_suffix(".json.part")
                tmp_meta.write_text(
                    json.dumps(fingerprint, ensure_ascii=False),
                    encoding="utf-8",
                )
                os.replace(tmp_meta, cache_meta)
                print(f"[MISU] Copia local lista: {cache_csv}")
                return cache_csv
            finally:
                if tmp_csv.exists():
                    tmp_csv.unlink()
        except (OSError, PermissionError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(1)

    raise OSError(
        "No fue posible copiar Base_M.csv desde la ruta de origen a un disco "
        "local despues de varios intentos. Comprueba la conexion a la red, "
        "que el CSV no este siendo actualizado y los permisos de lectura. "
        f"Origen: {source}. Cache: {cache_root}. Ultimo error: {last_error}"
    ) from last_error


def _read_base_csv(source: Path) -> pd.DataFrame:
    is_unc = str(source).startswith("\\\\")
    force_cache = os.getenv("LIQUIDITY_FORCE_LOCAL_CACHE", "0") == "1"

    # Evitar el parser C directamente sobre un archivo remoto grande.
    if is_unc or force_cache:
        local_csv = _base_csv_local_cache(source)
        return pd.read_csv(local_csv, encoding="cp1252", low_memory=False)

    # Fuentes locales: lectura normal, con fallback en caso de problemas de I/O.
    try:
        return pd.read_csv(source, encoding="cp1252", low_memory=False)
    except OSError as exc:
        print(f"[MISU] Fallo leyendo Base_M.csv directamente: {exc}")
        local_csv = _base_csv_local_cache(source)
        return pd.read_csv(local_csv, encoding="cp1252", low_memory=False)


BASE_PATH = _resolve_base_path()
print(f"[MISU] Origen de Base_M.csv: {BASE_PATH}")
Base = _read_base_csv(BASE_PATH)


# -----------------------------------------------------------------------------
# 2) NORMALIZACIÓN DE COLUMNAS
# -----------------------------------------------------------------------------
# El archivo Base_M real trae la contraparte bajo el encabezado '0'.
# El resto del dashboard trabaja con el nombre semántico 'Tipo de Contraparte'.
if "Tipo de Contraparte" not in Base.columns:
    if "0" in Base.columns:
        Base = Base.rename(columns={"0": "Tipo de Contraparte"})
    else:
        raise KeyError(
            "Base_M.csv no contiene la columna 'Tipo de Contraparte' ni la columna original '0'."
        )

# Elimina columnas auxiliares vacías que aparecen en algunos exports.
Base = Base.loc[:, ~Base.columns.astype(str).str.startswith("Unnamed:")].copy()


# -----------------------------------------------------------------------------
# 3) FECHAS
# -----------------------------------------------------------------------------
def _parse_date_series(s: pd.Series) -> pd.Series:
    """Convierte fechas dd/mm/YYYY y, si existieran, seriales de Excel."""
    raw = s.copy()
    parsed = pd.to_datetime(raw, format="%d/%m/%Y", errors="coerce")

    missing = parsed.isna()
    if missing.any():
        numeric = pd.to_numeric(raw[missing], errors="coerce")
        excel_dates = pd.Timestamp("1899-12-30") + pd.to_timedelta(numeric, unit="D")
        parsed.loc[missing] = excel_dates

    return parsed


Base["Día"] = _parse_date_series(Base["Día"])
Base = Base.dropna(subset=["Día", "Emisión", "Tipo", "Tipo de Contraparte"]).copy()

# Bono residual que el dashboard original ya excluía.
Base = Base[Base["Emisión"] != "PIPICP77U"].copy()

# Fecha de vencimiento: los últimos 6 dígitos de la emisión están en formato YYMMDD.
_maturity_token = Base["Emisión"].astype(str).str.extract(r"(\d{6})$")[0]
Base["Vencimiento"] = pd.to_datetime(_maturity_token, format="%y%m%d", errors="coerce")


# -----------------------------------------------------------------------------
# 4) TIPIFICACIÓN NUMÉRICA
# -----------------------------------------------------------------------------
NUMERIC_COLS = [
    "Compra Precio Máximo",
    "Compra Precio Mínimo",
    "Compra Precio Promedio",
    "Compra Número de Operaciones",
    "Venta Precio Máximo",
    "Venta Precio Mínimo",
    "Venta Precio Promedio",
    "Venta Número de Operaciones",
    "Número del promedio de Títulos por Operación",
    "Plazo por vencer de la Emisión",
    "Titulos Compras",
    "Titulos Ventas",
    "Titulos Compras más Ventas",
    "Número de Títulos en Circulación",
    "Volumen s/ Títulos Colocados",
    "USDMXN",
    "UDI",
    "Cupón",
    "Promedio YTM",
    "Duración",
]

for col in NUMERIC_COLS:
    if col in Base.columns:
        Base[col] = pd.to_numeric(Base[col], errors="coerce")


# -----------------------------------------------------------------------------
# 5) FILAS TOTAL POR EMISIÓN/DÍA/MERCADO
# -----------------------------------------------------------------------------
# IMPORTANTE: los totales se construyen SOBRE las contrapartes originales y luego
# se concatenan. Así evitamos doble conteo y conservamos las filas de participante.
AGGREGATIONS = {
    "Compra Precio Máximo": "mean",
    "Compra Precio Mínimo": "mean",
    "Compra Precio Promedio": "mean",
    "Compra Número de Operaciones": "sum",
    "Venta Precio Máximo": "mean",
    "Venta Precio Mínimo": "mean",
    "Venta Precio Promedio": "mean",
    "Venta Número de Operaciones": "sum",
    "Número del promedio de Títulos por Operación": "mean",
    "Plazo por vencer de la Emisión": "mean",
    "Titulos Compras": "sum",
    "Titulos Ventas": "sum",
    "Titulos Compras más Ventas": "sum",
    "Número de Títulos en Circulación": "mean",
    "Volumen s/ Títulos Colocados": "mean",
    "USDMXN": "mean",
    "UDI": "mean",
    "Cupón": "mean",
    "Promedio YTM": "mean",
    "Duración": "mean",
}
AGGREGATIONS = {k: v for k, v in AGGREGATIONS.items() if k in Base.columns}

_totales = (
    Base.groupby(["Día", "Emisión", "Tipo"], as_index=False, dropna=False)
    .agg(AGGREGATIONS)
)
_totales["Tipo de Contraparte"] = "Total"
_totales["Vencimiento"] = pd.to_datetime(
    _totales["Emisión"].astype(str).str.extract(r"(\d{6})$")[0],
    format="%y%m%d",
    errors="coerce",
)

Base = pd.concat([Base, _totales], ignore_index=True, sort=False)


# -----------------------------------------------------------------------------
# 6) MÉTRICAS DE LIQUIDEZ Y FLUJOS
# -----------------------------------------------------------------------------
# Valor nominal por título = 100 MXN / 100 UDIS según el instrumento.
Base["Volumen"] = Base["Titulos Compras más Ventas"] * 100.0 / 1_000_000.0
Base["Total N Operaciones"] = (
    Base["Compra Número de Operaciones"].fillna(0)
    + Base["Venta Número de Operaciones"].fillna(0)
)
Base["Ticket"] = Base["Volumen"] / Base["Total N Operaciones"].replace(0, np.nan)
Base["Turnover"] = (
    Base["Titulos Compras más Ventas"]
    / Base["Número de Títulos en Circulación"].replace(0, np.nan)
    * 100.0
)

# Mantiene la convención del dashboard histórico:
# positivo = Titulos Ventas - Titulos Compras.
Base["Compras netas nominal"] = (
    Base["Titulos Ventas"].fillna(0) * 100.0
    - Base["Titulos Compras"].fillna(0) * 100.0
)
Base["Compras netas mercado"] = (
    Base["Titulos Ventas"].fillna(0) * Base["Venta Precio Promedio"].fillna(0)
    - Base["Titulos Compras"].fillna(0) * Base["Compra Precio Promedio"].fillna(0)
)

# Udibonos: convierte nominal/volumen/ticket de UDI a MXN antes de expresar USD/DV01.
_mask_udi = Base["Tipo"].eq("UDIBONOS")
Base.loc[_mask_udi, "Volumen"] = Base.loc[_mask_udi, "Volumen"] * Base.loc[_mask_udi, "UDI"]
Base.loc[_mask_udi, "Compras netas nominal"] = (
    Base.loc[_mask_udi, "Compras netas nominal"] * Base.loc[_mask_udi, "UDI"]
)
Base.loc[_mask_udi, "Ticket"] = Base.loc[_mask_udi, "Ticket"] * Base.loc[_mask_udi, "UDI"]

# DataFrame canónico utilizado por todas las páginas.
KEEP_COLS = [
    "Día",
    "Emisión",
    "Tipo",
    "Tipo de Contraparte",
    "Volumen",
    "Número de Títulos en Circulación",
    "Titulos Compras más Ventas",
    "Plazo por vencer de la Emisión",
    "Total N Operaciones",
    "Ticket",
    "Turnover",
    "Compras netas nominal",
    "Compras netas mercado",
    "Vencimiento",
    "Compra Precio Promedio",
    "Venta Precio Promedio",
    "Cupón",
    "USDMXN",
    "Duración",
]
KEEP_COLS = [c for c in KEEP_COLS if c in Base.columns]
df_base = Base[KEEP_COLS].copy()

# Inf / -Inf no deben llegar a Plotly ni a Excel.
df_base = df_base.replace([np.inf, -np.inf], np.nan)

# Unidades históricas del dashboard:
# VolumenDV01 / TicketDV01: USDk de DV01 aproximado.
# Se conserva el signo histórico (-1) para no cambiar la convención existente.
_fx = df_base["USDMXN"].replace(0, np.nan)
_dur = df_base["Duración"]
df_base["VolumenDV01"] = (df_base["Volumen"] / _fx) * 0.1 * _dur * -1.0
df_base["TicketDV01"] = (df_base["Ticket"] / _fx) * 0.1 * _dur * -1.0

df_base["Compras netas USD"] = (
    df_base["Compras netas nominal"] / _fx / 1_000_000.0
)
df_base["ComprasnetasnominalDV01"] = (
    df_base["Compras netas USD"] * 0.1 * _dur * -1.0
)

df_base["Mensual"] = df_base["Día"].dt.to_period("M").dt.to_timestamp()
df_base["Anual"] = df_base["Día"].dt.year


# -----------------------------------------------------------------------------
# 7) LISTAS Y METADATOS COMPATIBLES CON EL DASHBOARD ORIGINAL
# -----------------------------------------------------------------------------
fecha_maxima = df_base["Día"].max()
fecha_minima = df_base["Día"].min()
max_anio = int(fecha_maxima.year)
min_anio = int(fecha_minima.year)
todos_los_anios = sorted(df_base["Anual"].dropna().astype(int).unique().tolist())


def _active_emissions(market: str) -> list[str]:
    # Activos a la última fecha disponible EN LA BASE, no al reloj del sistema.
    # Esto hace reproducible un dashboard con data histórica.
    d = (
        df_base.loc[df_base["Tipo"].eq(market), ["Emisión", "Vencimiento"]]
        .drop_duplicates()
        .dropna(subset=["Emisión"])
    )
    d = d[(d["Vencimiento"].isna()) | (d["Vencimiento"] > fecha_maxima)]
    d = d.sort_values(["Vencimiento", "Emisión"], na_position="last")
    return d["Emisión"].astype(str).tolist()


lista_resultado_ms = _active_emissions("BONOTF") + ["Total"]
lista_resultado_udis = _active_emissions("UDIBONOS") + ["Total"]
