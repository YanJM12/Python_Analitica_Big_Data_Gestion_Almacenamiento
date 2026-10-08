import mysql.connector
import pandas as pd
import re
import unicodedata


def limpiar_nombre_columna(nombre):
    """
    Convierte el nombre original en un nombre seguro para MySQL.
    """

    nombre = str(nombre)

    # Quitar tildes y caracteres Unicode
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = nombre.encode(
        "ascii", "ignore"
    ).decode("ascii")

    # Convertir todo a minúsculas
    nombre = nombre.lower()

    # Reemplazar cualquier cosa que no sea letra o número por _
    nombre = re.sub(
        r"[^a-zA-Z0-9_]",
        "_",
        nombre
    )

    # Evitar múltiples _
    nombre = re.sub(
        r"_+",
        "_",
        nombre
    )

    # Quitar _ al principio y al final
    nombre = nombre.strip("_")

    # Si queda vacío
    if not nombre:
        nombre = "columna"

    # Máximo 64 caracteres de MySQL
    nombre = nombre[:64]

    return nombre


def cargar_datos_mysql(
    df: pd.DataFrame,
    nombre_archivo: str
):

    print(
        f"\nEmpezando a guardar {nombre_archivo}"
    )

    # ============================================================
    # 1. GUARDAR CSV Y JSON ORIGINALES
    # ============================================================

    df.to_csv(
        f"data/gold/{nombre_archivo}.csv",
        index=False,
        encoding="utf-8-sig",
        na_rep=""
    )

    df.to_json(
        f"data/gold/{nombre_archivo}.json",
        orient="records",
        force_ascii=False
    )

    # ============================================================
    # 2. CONECTAR CON MYSQL EN DOCKER
    # ============================================================

    conexion = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="root",
        database="ipm"
    )

    cursor = conexion.cursor()

    # ============================================================
    # 3. CREAR NOMBRES SEGUROS PARA MYSQL
    # ============================================================

    nombres_mysql = []
    usados = set()

    for columna in df.columns:

        nombre_mysql = limpiar_nombre_columna(
            columna
        )

        nombre_base = nombre_mysql
        contador = 1

        # Evitar nombres duplicados
        while nombre_mysql in usados:

            sufijo = f"_{contador}"

            nombre_mysql = (
                nombre_base[
                    :64 - len(sufijo)
                ]
                + sufijo
            )

            contador += 1

        usados.add(nombre_mysql)

        nombres_mysql.append(
            nombre_mysql
        )

    # ============================================================
    # 4. DETERMINAR LOS TIPOS DE DATOS
    # ============================================================

    columnas_sql = []

    for columna_original, nombre_mysql in zip(
        df.columns,
        nombres_mysql
    ):

        if pd.api.types.is_integer_dtype(
            df[columna_original]
        ):

            tipo = "BIGINT"

        elif pd.api.types.is_float_dtype(
            df[columna_original]
        ):

            tipo = "DOUBLE"

        elif pd.api.types.is_bool_dtype(
            df[columna_original]
        ):

            tipo = "BOOLEAN"

        elif pd.api.types.is_datetime64_any_dtype(
            df[columna_original]
        ):

            tipo = "DATETIME"

        else:

            tipo = "TEXT"

        columnas_sql.append(
            f"{nombre_mysql} {tipo}"
        )

    estructura = ", ".join(
        columnas_sql
    )

    # ============================================================
    # 5. ELIMINAR TABLA SI YA EXISTE
    # ============================================================

    cursor.execute(
        f"DROP TABLE IF EXISTS {nombre_archivo}"
    )

    # ============================================================
    # 6. CREAR TABLA
    # ============================================================

    sql_create = (
        f"CREATE TABLE {nombre_archivo} "
        f"({estructura})"
    )

    cursor.execute(
        sql_create
    )

    print(
        f"Tabla {nombre_archivo} creada correctamente"
    )

    # ============================================================
    # 7. INSERTAR LOS DATOS
    # ============================================================

    nombres_columnas = ", ".join(
        f"{columna}"
        for columna in nombres_mysql
    )

    placeholders = ", ".join(
        ["%s"] * len(df.columns)
    )

    sql_insert = f"""
        INSERT INTO {nombre_archivo}
        ({nombres_columnas})
        VALUES ({placeholders})
    """

    # ============================================================
    # 8. PREPARAR DATOS
    # ============================================================

    datos = []

    for fila in df.itertuples(
        index=False,
        name=None
    ):

        datos.append(
            tuple(
                None if pd.isna(valor)
                else valor
                for valor in fila
            )
        )

    # ============================================================
    # 9. INSERTAR EN MYSQL
    # ============================================================

    cursor.executemany(
        sql_insert,
        datos
    )

    conexion.commit()

    # ============================================================
    # 10. CERRAR CONEXIÓN
    # ============================================================

    cursor.close()
    conexion.close()

    print(
        f"Datos de {nombre_archivo} "
        f"cargados correctamente en MySQL"
    )

    print(
        "Dimensiones:",
        df.shape
    )

    print(
        "Cantidad de columnas:",
        len(df.columns)
    )