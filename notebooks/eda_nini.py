# -*- coding: utf-8 -*-
"""
Análisis exploratorio (EDA) - Población NINI entre 18 y 28 años (Colombia)
Incluye: carga robusta, limpieza, normalización, detección de outliers,
análisis univariado/bivariado/temporal y exportación de datos limpios.

Uso:  python eda_nini.py  [ruta_al_csv]
"""
import io
import sys
import unicodedata
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # quita esta línea si usas Jupyter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

RUTA = Path(sys.argv[1] if len(sys.argv) > 1 else "población_nini_entre_18_Y_28_anios_2025.csv")
SALIDA = Path("salida_eda")
SALIDA.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid")


# ---------------------------------------------------------------
# 1. CARGA ROBUSTA
# El archivo trae cada fila envuelta en comillas ("...") con comillas
# internas duplicadas (""), por eso pd.read_csv normal lee 1 sola columna.
# ---------------------------------------------------------------
def cargar_csv(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, encoding="utf-8-sig")
    if df.shape[1] == 1:  # formato doblemente entrecomillado
        lineas = df.columns.tolist() + df.iloc[:, 0].astype(str).tolist()
        df = pd.read_csv(io.StringIO("\n".join(lineas)), skipinitialspace=True)
    return df


df_raw = cargar_csv(RUTA)
print("=== 1. CARGA ===")
print("Dimensiones:", df_raw.shape)
print(df_raw.head(), "\n")
df_raw.info()


# ---------------------------------------------------------------
# 2. LIMPIEZA
# ---------------------------------------------------------------
def quitar_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def snake(s: str) -> str:
    return quitar_tildes(s).strip().lower().replace(" ", "_")


df = df_raw.copy()

# 2.1 Nombres de columnas -> snake_case sin tildes (y corrige "Periocidad")
df.columns = [snake(c) for c in df.columns]
df = df.rename(columns={"periocidad": "periodicidad",
                        "desagregacion_geografica": "nivel_geografico",
                        "dominio_geografico": "territorio",
                        "ano": "anio"})

# 2.2 Texto: espacios sobrantes y comillas residuales
for c in df.select_dtypes(include=["object", "string"]).columns:
    df[c] = df[c].astype(str).str.strip().str.strip('"').str.strip()

# 2.3 Tipos de dato
df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
df["valor"] = pd.to_numeric(df["valor"].astype(str).str.replace(",", "."), errors="coerce")
df["nivel_geografico"] = df["nivel_geografico"].astype("category")

# 2.4 Columnas constantes (no aportan información) -> se eliminan
constantes = [c for c in df.columns if df[c].nunique(dropna=False) == 1]
print("\n=== 2. LIMPIEZA ===\nColumnas constantes eliminadas:", constantes)
metadatos = {c: df[c].iloc[0] for c in constantes}
df = df.drop(columns=constantes)

# 2.5 Nulos y duplicados
print("Nulos por columna:\n", df.isna().sum())
n0 = len(df)
df = df.dropna(subset=["valor", "anio", "territorio"])
df = df.drop_duplicates()
print(f"Filas eliminadas por nulos/duplicados: {n0 - len(df)}")

# 2.6 Validación de rango (es un porcentaje: 0-100)
fuera = df[(df["valor"] < 0) | (df["valor"] > 100)]
print("Filas con porcentaje fuera de [0, 100]:", len(fuera))
df = df.drop(fuera.index)

# 2.7 Integridad del panel: ¿cada territorio tiene todos los años?
esperado = df["anio"].nunique()
cobertura = df.groupby("territorio")["anio"].nunique()
incompletos = cobertura[cobertura < esperado]
print("Territorios con años faltantes:", incompletos.to_dict() or "ninguno")

# 2.8 Separar nacional vs departamental (evita mezclar niveles al comparar)
nacional = df[df["nivel_geografico"] == "Nacional"].sort_values("anio")
depto = df[df["nivel_geografico"] == "Departamental"].copy()
print(f"Años cubiertos: {df['anio'].min()} - {df['anio'].max()}")
print(f"Departamentos/ciudades: {depto['territorio'].nunique()}")


# ---------------------------------------------------------------
# 3. ESTADÍSTICA DESCRIPTIVA
# ---------------------------------------------------------------
print("\n=== 3. DESCRIPTIVA ===")
print(depto["valor"].describe().round(2))
print("Asimetría:", round(depto["valor"].skew(), 3), "| Curtosis:", round(depto["valor"].kurt(), 3))

resumen = (depto.groupby("territorio")["valor"]
           .agg(media="mean", mediana="median", desv="std", minimo="min", maximo="max")
           .round(2).sort_values("media", ascending=False))
resumen["cv_%"] = (resumen["desv"] / resumen["media"] * 100).round(1)  # coef. de variación
print("\nTop 5 mayor NINI promedio:\n", resumen.head(5))
print("\nTop 5 menor NINI promedio:\n", resumen.tail(5))


# ---------------------------------------------------------------
# 4. OUTLIERS (IQR global y z-score dentro de cada año)
# ---------------------------------------------------------------
q1, q3 = depto["valor"].quantile([0.25, 0.75])
iqr = q3 - q1
lim_inf, lim_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
depto["outlier_iqr"] = ~depto["valor"].between(lim_inf, lim_sup)
depto["z_anio"] = depto.groupby("anio")["valor"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
depto["outlier_z"] = depto["z_anio"].abs() > 2
print("\n=== 4. OUTLIERS ===")
print(f"Límites IQR: [{lim_inf:.2f}, {lim_sup:.2f}] -> {depto['outlier_iqr'].sum()} atípicos")
print(depto.loc[depto["outlier_z"], ["territorio", "anio", "valor", "z_anio"]]
      .round(2).sort_values("z_anio").to_string(index=False))
# Decisión: en datos oficiales un valor extremo suele ser real (no error).
# Se MARCA pero no se elimina. Para eliminar: depto = depto[~depto["outlier_iqr"]]


# ---------------------------------------------------------------
# 5. NORMALIZACIÓN / TRANSFORMACIONES
# ---------------------------------------------------------------
depto["valor_zscore"] = (depto["valor"] - depto["valor"].mean()) / depto["valor"].std()
depto["valor_minmax"] = (depto["valor"] - depto["valor"].min()) / (depto["valor"].max() - depto["valor"].min())
# Diferencia respecto al promedio nacional del mismo año (brecha en puntos porcentuales)
nac_anio = nacional.set_index("anio")["valor"]
depto["brecha_vs_nacional_pp"] = depto["valor"] - depto["anio"].map(nac_anio)
# Cambio porcentual año a año por territorio
depto = depto.sort_values(["territorio", "anio"])
depto["var_anual_pp"] = depto.groupby("territorio")["valor"].diff()

# Formato ancho (territorio x año) para heatmaps / clustering
ancho = depto.pivot(index="territorio", columns="anio", values="valor")


# ---------------------------------------------------------------
# 6. TENDENCIAS Y CAMBIO 2008 -> ÚLTIMO AÑO
# ---------------------------------------------------------------
a0, a1 = int(depto["anio"].min()), int(depto["anio"].max())
cambio = (ancho[a1] - ancho[a0]).sort_values().rename(f"cambio_pp_{a0}_{a1}")
pendiente = ancho.apply(lambda r: np.polyfit(ancho.columns.astype(float), r.values, 1)[0], axis=1)
print(f"\n=== 6. TENDENCIAS ===\nMayor reducción {a0}->{a1} (pp):\n", cambio.head(5).round(1))
print("\nMenor reducción / aumento:\n", cambio.tail(5).round(1))
print("\nPendiente media anual (pp/año), nacional aprox.:", round(pendiente.mean(), 2))

# Correlación entre años (¿el ranking territorial es estable?)
print("\nCorrelación (Spearman) entre primer y último año:",
      round(ancho[a0].corr(ancho[a1], method="spearman"), 3))


# ---------------------------------------------------------------
# 7. GRÁFICOS
# ---------------------------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
sns.histplot(depto["valor"], kde=True, ax=ax[0], color="#2a6f97")
ax[0].set(title="Distribución del % NINI (departamental)", xlabel="% NINI")
sns.boxplot(data=depto, x="anio", y="valor", ax=ax[1], color="#a9d6e5")
ax[1].set(title="Distribución por año", xlabel="Año", ylabel="% NINI")
plt.tight_layout(); plt.savefig(SALIDA / "01_distribucion.png", dpi=150); plt.close()

plt.figure(figsize=(11, 6))
for t, g in depto.groupby("territorio"):
    plt.plot(g["anio"], g["valor"], color="grey", alpha=0.3, lw=1)
plt.plot(nacional["anio"], nacional["valor"], color="crimson", lw=3, label="Colombia")
plt.title("Evolución del % NINI: departamentos (gris) vs. nacional"); plt.xlabel("Año"); plt.ylabel("% NINI")
plt.legend(); plt.tight_layout(); plt.savefig(SALIDA / "02_evolucion.png", dpi=150); plt.close()

orden = resumen.sort_values("media").index
plt.figure(figsize=(8, 9))
sns.barplot(x=resumen.loc[orden, "media"], y=orden, color="#2a6f97")
plt.axvline(nacional["valor"].mean(), color="crimson", ls="--", label="Promedio nacional")
plt.title("% NINI promedio por territorio"); plt.xlabel("% NINI"); plt.legend()
plt.tight_layout(); plt.savefig(SALIDA / "03_ranking.png", dpi=150); plt.close()

plt.figure(figsize=(11, 9))
sns.heatmap(ancho.loc[resumen.index], cmap="YlOrRd", annot=True, fmt=".0f", cbar_kws={"label": "% NINI"})
plt.title("Mapa de calor: territorio x año"); plt.tight_layout()
plt.savefig(SALIDA / "04_heatmap.png", dpi=150); plt.close()

plt.figure(figsize=(8, 7))
cambio.sort_values().plot.barh(color=np.where(cambio.sort_values() < 0, "#2a9d8f", "#e76f51"))
plt.title(f"Cambio en el % NINI {a0}→{a1} (puntos porcentuales)")
plt.tight_layout(); plt.savefig(SALIDA / "05_cambio.png", dpi=150); plt.close()


# ---------------------------------------------------------------
# 8. EXPORTAR
# ---------------------------------------------------------------
depto.to_csv(SALIDA / "nini_limpio_largo.csv", index=False, encoding="utf-8-sig")
ancho.to_csv(SALIDA / "nini_ancho.csv", encoding="utf-8-sig")
resumen.to_csv(SALIDA / "nini_resumen_territorio.csv", encoding="utf-8-sig")
print(f"\nListo. Archivos en: {SALIDA.resolve()}")
print("Metadatos (columnas constantes):", metadatos)
