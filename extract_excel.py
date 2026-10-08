
import pandas as pd

def extraer_datos(ruta:str)->pd.DataFrame:
    print("Empezando a extraer hogares IMP")
    df_extraido_hogares_ipm = pd.read_csv(ruta)
    

    return df_extraido_hogares_ipm

def extraccion_nini(ruta1:str)->pd.DataFrame:
    print("Empezando a extraer nini")
    df_extraido_nini = pd.read_csv(ruta1)


    return df_extraido_nini

def extraccion_variables(ruta2:str)->pd.DataFrame:
    print("Exmpezando a extraer variables")
    df_extraido_variables = pd.read_csv(ruta2)


    return df_extraido_variables