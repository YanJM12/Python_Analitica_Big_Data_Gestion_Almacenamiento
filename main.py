import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yaml
import openpyxl
import csv


#Las librerias del modulo
import src.extract.extract_excel as IPM 
import src.transform.clean_excel as transform
import src.load.load_database as load
import src.extract.extract_excel as nini
import src.extract.extract_excel as variables


def main():

    #Leer archivo yaml

    with open("config/config.yaml", "r") as file:
        config = yaml.safe_load(file)

    #EXTRACCION 

    #llamado a extraer los datos desde el csv de hogares IPM
    df_extraido_hogares_IPM = IPM.extraer_datos(config['sources']['hogares_ipm']['path'])
    print(df_extraido_hogares_IPM)


    #llamado a extraer los datos desde el csv nini
    df_extraido_nini = nini.extraccion_nini(config['sources']['poblacion_nini']['path'])
    print(df_extraido_nini)

    #llamado a extraer los datosdesde el csv variables
    df_extraido_variables = variables.extraccion_variables(config['sources']['ipm_variables']['path'])
    print(df_extraido_variables)


    #LIMPIEZA

    #Transformacion
    df_transformado_hogares_IPM = transform.limpiar_datos(df_extraido_hogares_IPM)
    print(df_transformado_hogares_IPM)

    df_transformado_variables = transform.limpiar_datos3(df_extraido_variables)
    print(df_transformado_variables)

    df_transformado_nini = transform.limpiar_datos2(df_extraido_nini)
    print(df_transformado_nini)


    #CARGA

    #Carga de datos
    load.cargar_datos_mysql(df_transformado_hogares_IPM, "hogares_IPM")
    load.cargar_datos_mysql(df_transformado_variables, "variables_IPM")
    load.cargar_datos_mysql(df_transformado_nini,"Jovenes_NINI")


if __name__ == "__main__":
    main()


