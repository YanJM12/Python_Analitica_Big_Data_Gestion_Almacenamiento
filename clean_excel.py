import pandas as pd
import os
import csv
import unicodedata

def limpiar_datos(df: pd.DataFrame)-> pd.DataFrame:
    print("Empezando a limpiar los datos")

    # Obtener los nombres de las columnas
    encabezado = df.columns[0]
    columnas = next(csv.reader([encabezado], skipinitialspace=True))
    columnas = [col.strip().strip('"') for col in columnas]

    # Separar correctamente los datos
    filas = []
    for fila in df.iloc[:, 0].astype(str):
        fila_separada = next(csv.reader([fila], skipinitialspace=True))
        filas.append(fila_separada)

    datos = pd.DataFrame(filas, columns=columnas)

    # Limpiar espacios y comillas
    for columna in datos.columns:
        datos[columna] = datos[columna].str.strip().str.strip('"')

    # Reemplazar valores vacíos por NA en ciudades capitales
    datos["Ciudades capitales (sin A.M.)"] = (
        datos["Ciudades capitales (sin A.M.)"].replace("", "NA")
    )
    
    print(
        "\nValores NA en Ciudades capitales:",
        (datos["Ciudades capitales (sin A.M.)"] == "NA").sum()
    )


    # Revisar dimensiones
    print("\nDimensiones:", datos.shape)
    print("Cantidad de columnas:", len(datos.columns))
    print("Columnas:", datos.columns.tolist())

    # Revisar valores vacíos
    print("\nValores vacíos por columna:")
    vacios = datos.eq("").sum()
    print(vacios[vacios > 0] if (vacios > 0).any() else "No se encontraron")

    # Revisar duplicados sin eliminarlos
    duplicados = datos.duplicated().sum()
    print("\nRegistros duplicados encontrados:", duplicados)

    # Mostrar las primeras filas
    print("\nPrimeras filas:")
    print(datos.head())

    # Información general
    datos.info(verbose=True)

    return datos




def limpiar_datos2(df: pd.DataFrame) -> pd.DataFrame:
 

    print("Iniciando la limpieza de datos NINI...")

    # Crear una copia para no modificar el DataFrame original.
    df = df.copy()

    # 1. NORMALIZACIÓN DE NOMBRES DE COLUMNAS


    def quitar_tildes(s: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFD", str(s))
            if unicodedata.category(c) != "Mn"
        )

    def snake(s: str) -> str:
        return quitar_tildes(s).strip().lower().replace(" ", "_")

    df.columns = [snake(c) for c in df.columns]

    # Correcciones de nombres de columnas
    df = df.rename(
        columns={
            "periocidad": "periodicidad",
            "desagregacion_geografica": "nivel_geografico",
            "dominio_geografico": "territorio",
            "ano": "anio"
        }
    )

    # 2. LIMPIEZA DE TEXTO

    for columna in df.select_dtypes(
        include=["object", "string"]
    ).columns:
        df[columna] = (
            df[columna]
            .astype(str)
            .str.strip()
            .str.strip('"')
            .str.strip()
        )

    # 3. CONVERSIÓN DE TIPOS


    if "anio" in df.columns:
        df["anio"] = pd.to_numeric(
            df["anio"],
            errors="coerce"
        ).astype("Int64")

    if "valor" in df.columns:
        df["valor"] = pd.to_numeric(
            df["valor"]
            .astype(str)
            .str.replace(",", ".", regex=False),
            errors="coerce"
        )

    if "nivel_geografico" in df.columns:
        df["nivel_geografico"] = df["nivel_geografico"].astype("category")


    # 4. ELIMINAR COLUMNAS CONSTANTES

    constantes = [
        c for c in df.columns
        if df[c].nunique(dropna=False) == 1
    ]

    print("\nColumnas constantes eliminadas:", constantes)

    df = df.drop(columns=constantes)


    # 5. VALORES NULOS Y DUPLICADOS

    print("\nNulos por columna:")
    print(df.isna().sum())

    n0 = len(df)

    columnas_obligatorias = [
        c for c in ["valor", "anio", "territorio"]
        if c in df.columns
    ]

    if columnas_obligatorias:
        df = df.dropna(subset=columnas_obligatorias)

    df = df.drop_duplicates()

    print(
        f"\nFilas eliminadas por nulos/duplicados: "
        f"{n0 - len(df)}"
    )


    # 6. VALIDACIÓN DEL RANGO DEL PORCENTAJE


    if "valor" in df.columns:
        fuera = df[
            (df["valor"] < 0) |
            (df["valor"] > 100)
        ]

        print(
            "Filas con porcentaje fuera de [0, 100]:",
            len(fuera)
        )

        df = df.drop(fuera.index)

 
    # 7. INFORMACIÓN DE COBERTURA TEMPORAL


    if {"territorio", "anio"}.issubset(df.columns):
        esperado = df["anio"].nunique()

        cobertura = (
            df.groupby("territorio", observed=True)["anio"]
            .nunique()
        )

        incompletos = cobertura[cobertura < esperado]

        print(
            "Territorios con años faltantes:",
            incompletos.to_dict() or "ninguno"
        )


    # 8. SEPARAR NIVEL NACIONAL Y DEPARTAMENTAL


    if "nivel_geografico" in df.columns:
        nacional = df[
            df["nivel_geografico"] == "Nacional"
        ].sort_values("anio")

        depto = df[
            df["nivel_geografico"] == "Departamental"
        ].copy()

        print(
            f"Años cubiertos: "
            f"{df['anio'].min()} - {df['anio'].max()}"
        )

        print(
            f"Departamentos/ciudades: "
            f"{depto['territorio'].nunique()}"
        )


    # 9. INFORMACIÓN FINAL


    print("\nDimensiones finales:", df.shape)
    print("Columnas finales:", df.columns.tolist())

    print("\nPrimeras filas:")
    print(df.head())

    print("\nLimpieza de datos NINI completada.")

    return df


def limpiar_datos3(df: pd.DataFrame) -> pd.DataFrame:

    print("Iniciando la limpieza de datos...")

    # Se crea una copia para evitar modificar directamente el DataFrame
    # original que proviene de la capa Bronze.
    df = df.copy()

    # El código DANE de los departamentos debe tener dos dígitos.
    #
    # Por ejemplo:
    # 5  -> "05"
    # 8  -> "08"
    # 11 -> "11"
    #
    # Primero se convierte a texto y posteriormente se agregan ceros
    # a la izquierda cuando sea necesario.
    df["cod_dane"] = (
        df["cod_dane"]
        .astype(str)
        .str.zfill(2)
    )

    # Se identifican las filas que no tienen información en "valor_pct".
    #
    # Estos registros no se pueden utilizar para el análisis porcentual,
    # pero antes de excluirlos se guardan como evidencia en la carpeta
    # de logs.
    sin_valor = df[df["valor_pct"].isnull()].copy()

    # Crear la carpeta logs si todavía no existe.
    os.makedirs("../logs", exist_ok=True)

    # Guardar los registros excluidos.
    sin_valor.to_csv(
        "../logs/ipm_filas_excluidas.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # Excluir del DataFrame los registros que no tienen valor_pct.
    df = df[df["valor_pct"].notnull()].copy()

    # Cuando no existe una nota asociada al año, se reemplaza el valor
    # nulo por la categoría "Sin nota".
    #
    # De esta manera se evita conservar valores NaN en esta variable
    # y se mantiene explícitamente la información de que no existe nota.
    df["nota_anio"] = df["nota_anio"].fillna("Sin nota")

    # Se crea una nueva columna para registrar posibles situaciones
    # que requieren revisión.
    #
    # Inicialmente todos los registros se consideran sin alerta.
    df["alerta_calidad"] = "Sin alerta"

    # Se identifican porcentajes exactamente iguales a 0 o 100.
    # Estos valores no se eliminan porque pueden ser datos válidos.
    # Únicamente se marcan como una alerta para facilitar su revisión.
    df.loc[
        df["valor_pct"].isin([0, 100]),
        "alerta_calidad"
    ] = "Valor extremo (0 o 100)"

     # Para cada departamento, variable y año se comparan los valores
    # correspondientes a:
    # - Total
    # - Cabeceras
    # - Centros poblados y rural disperso
    # El objetivo es identificar casos en los que el valor Total se
    # encuentre fuera del rango de las dos zonas.
    
    p = (
        df.pivot_table(
            index=["cod_dane", "variable", "anio"],
            columns="zona",
            values="valor_pct"
        )
        .dropna(
            subset=[
                "Total",
                "Cabeceras",
                "Centros poblados y rural disperso"
            ]
        )
    )

    # Seleccionar únicamente las dos zonas que se utilizarán
    # como referencia para la comparación.
    zonas = p[
        [
            "Cabeceras",
            "Centros poblados y rural disperso"
        ]
    ]

    # Identificar los casos en los que el Total se encuentra por fuera
    # del rango de las dos zonas.
    #
    # Se utiliza una tolerancia de 0.1 debido a posibles diferencias
    # ocasionadas por el redondeo de los porcentajes.
    fuera = p[
        (p["Total"] < zonas.min(axis=1) - 0.1) |
        (p["Total"] > zonas.max(axis=1) + 0.1)
    ]

    # Obtener las llaves de los registros que presentan inconsistencias.
    llaves = (
        fuera
        .reset_index()[
            ["cod_dane", "variable", "anio"]
        ]
        .copy()
    )

    # Crear una marca para identificar las combinaciones inconsistentes.
    llaves["inconsistente"] = True

    # Unir la información de las inconsistencias con el DataFrame original.
    tmp = df.merge(
        llaves,
        on=["cod_dane", "variable", "anio"],
        how="left"
    )

    # Identificar las filas que presentan inconsistencia.
    mascara = tmp["inconsistente"].eq(True).to_numpy()

    # Registrar la alerta en el DataFrame.
    df.loc[
        mascara,
        "alerta_calidad"
    ] = "Total fuera del rango cabeceras-rural"

  
    # VALIDAR REGISTROS DUPLICADOS
 
    duplicados = df.duplicated(
        [
            "cod_dane",
            "variable",
            "anio",
            "zona"
        ]
    ).sum()

    assert duplicados == 0, (
        f"Se encontraron {duplicados} registros duplicados."
    )

    # VALIDAR EL RANGO DE LOS PORCENTAJES
    assert df["valor_pct"].between(0, 100).all(), (
        "Existen valores de valor_pct fuera del rango 0-100."
    )

    # Después de realizar el tratamiento de valores faltantes,
    # se verifica que no existan valores nulos en el DataFrame.
   
    assert df.isnull().sum().sum() == 0, (
        "Existen valores nulos después de la limpieza."
    )

    # Colombia cuenta con 32 departamentos y Bogotá D.C.,
    # por lo que se esperan 33 códigos territoriales.
 
    assert df["departamento"].nunique() == 33, (
        "El DataFrame no contiene los 33 departamentos."
    )

    print("Limpieza y validaciones completadas correctamente.")

    # Retornar el DataFrame limpio.

    return df