import pandas as pd
import mysql.connector

def cargar_datos(df_final, table_name="tabla_etl"):
    print("Iniciando carga de datos...")

    #Conexión
    conn = mysql.connector.connect
    

