import pandas as pd
from urllib.parse import quote
import time
import random
import os
from utils import (
    extract_asignatura,
    scrapBibliography,
    scrapGoogleScholar,
    extraer_resultados_aprendizaje,
    extraer_competencias,
    extraer_conocimientos_previos,
    scrapProfesores,
    estructurar_temario,
    extraer_descripcion_asignatura,
    extraer_temario_asignatura,
    extraer_criterios_evaluacion,
    bulk_index_data
)
from elasticsearch import Elasticsearch
from sqlalchemy import create_engine 
import re
from sentence_transformers import SentenceTransformer

# Pasos Pipeline
# 1 - MetaDatos de la asignatura
directory = "Guias Docentes"
df_bibliografia_total = pd.DataFrame()
df_bibliografia_asignatura = pd.DataFrame()
df_profesores_total = pd.DataFrame()
df_profesores_asignaturas_total = pd.DataFrame()
df_asignaturas_total = pd.DataFrame()
df_escuelas_total = pd.DataFrame()
df_titulaciones_total = pd.DataFrame()
df_titulaciones_escuelas_total = pd.DataFrame()
df_titulaciones_asignaturas_total = pd.DataFrame()


for file in os.listdir(directory):
    if file.endswith(".pdf"):  
        pdf_path = os.path.join(directory, file)

        # asignatura
        df_asignatura = extract_asignatura(pdf_path)
        id_asignatura, nombre_asignatura = df_asignatura['Nombre de la asignatura'].values[0].split(" - ", maxsplit=1)
        num_creditos = df_asignatura['No de créditos'].values[0].split(" ")[0]
        curso_texto = df_asignatura['Curso'].values[0]
        semestre_texto = df_asignatura['Semestre'].values[0]
        idioma = df_asignatura['Idioma de impartición'].values[0]
        plan_estudios, nombre_titulacion = df_asignatura['Titulación'].values[0].split(" - ", maxsplit=1)
        id_escuela, nombre_escuela = df_asignatura['Centro responsable de la\ntitulación'].values[0].split(" - ", maxsplit=1)
        curso_academico = df_asignatura['Curso académico'].values[0]
        
        df_asignatura = pd.DataFrame([{
            "id": id_asignatura,
            "nombre": nombre_asignatura,
            "numero_creditos": num_creditos,
            "agno_academico": curso_texto,
            "semestre": semestre_texto,
            "idioma": idioma
        }])
        df_asignaturas_total = pd.concat([df_asignaturas_total, df_asignatura], ignore_index=True)
        
        if df_titulaciones_total.empty or plan_estudios not in df_titulaciones_total['id'].values:
            df_titulacion = pd.DataFrame([{
                "id": plan_estudios,
                "nombre": nombre_titulacion,
                "tipo_estudio": "Grado" if "Grado" in plan_estudios else "Máster"
            }])
            df_titulaciones_total = pd.concat([df_titulaciones_total, df_titulacion], ignore_index=True)

        if df_escuelas_total.empty or id_escuela not in df_escuelas_total['id'].values:
            df_escuela = pd.DataFrame([{
                "id": id_escuela,
                "nombre": nombre_escuela
            }])
            df_escuelas_total = pd.concat([df_escuelas_total, df_escuela], ignore_index=True)

        if df_titulaciones_escuelas_total.empty or df_titulaciones_escuelas_total.get((df_titulaciones_escuelas_total['titulacion_id'] == plan_estudios) & (df_titulaciones_escuelas_total['escuela_id'] == id_escuela)).any().any() == False:
            df_titulacion_escuela = pd.DataFrame([{
                "titulacion_id": plan_estudios,
                "escuela_id": id_escuela
            }])
            df_titulaciones_escuelas_total = pd.concat([df_titulaciones_escuelas_total, df_titulacion_escuela], ignore_index=True)
        
        df_titulacion_asignatura = pd.DataFrame([{
            "titulacion_id": plan_estudios,
            "asignatura_id": id_asignatura
        }])
        df_titulaciones_asignaturas_total = pd.concat([df_titulaciones_asignaturas_total, df_titulacion_asignatura], ignore_index=True)

        # Bibliografia
        df_scrap_bibliografia = scrapBibliography(pdf_path, {"nombre", "tipo", "observaciones"})  

        dfs_bibliografia = []
        
        for nombre in df_scrap_bibliografia['Nombre']:
            try:
                dict_bibliografia = scrapGoogleScholar(nombre)
                df_temp = pd.DataFrame([dict_bibliografia])
                dfs_bibliografia.append(df_bibliografia)
            except Exception as e:
                print(f"Error con {nombre}: {e}")

            time.sleep(random.uniform(5, 15))

        if dfs_bibliografia != []:
            df_bibliografia = pd.concat(dfs_bibliografia, ignore_index=True)
            df_bibliografia_total =  pd.concat([df_bibliografia_total, dfs_bibliografia], ignore_index=True).drop_duplicates()
            list_bibliografias = df_bibliografia_total['Nombre'].unique()
            df_bibliografia_asignatura = pd.concat([df_bibliografia_asignatura,pd.DataFrame({'Nombre':list_bibliografias, 'id_asignatura': [id_asignatura]*len(list_bibliografias)})])

        # Profesores
        df_profesores = scrapProfesores(pdf_path, {"nombre", "correo electrónico"})
        print('profes')
        print(df_profesores)
        print()
        if not df_profesores_total.empty:
            df_profesores_total = pd.concat([df_profesores_total, df_profesores], ignore_index=True)
            df_profesores_total = df_profesores_total.drop_duplicates(
                subset="Correo electrónico",
                keep="first",
                ignore_index=True
            )
        else:
            df_profesores_total = df_profesores.copy()
        
        # Profesores - Asignaturas
        df_profesores_asignaturas = pd.DataFrame()
        for _, row in df_profesores.iterrows():
            profesor_correo = row["Correo electrónico"]
            try:
                profesor_id = df_profesores_total.index[df_profesores_total["Correo electrónico"] == profesor_correo][0]
            except IndexError:
                continue
            df_temp = pd.DataFrame([{
                "profesor_id": profesor_id,
                "asignatura_id": id_asignatura
            }])
            df_profesores_asignaturas = pd.concat([df_profesores_asignaturas, df_temp], ignore_index=True)
        if not df_profesores_asignaturas_total.empty:
            df_profesores_asignaturas_total = pd.concat([df_profesores_asignaturas_total, df_profesores_asignaturas], ignore_index=True)
        else:
            df_profesores_asignaturas_total = df_profesores_asignaturas.copy()

print('HEMOS LLEGADO AL FINAL')

print('df_asignaturas_total:', df_asignaturas_total.head())
print('df_escuelas_total:', df_escuelas_total.head())
print('df_titulaciones_total:', df_titulaciones_total.head())
print('df_bibliografia_total:', df_bibliografia_total.head())
print('df_profesores_total:', df_profesores_total.head())
print('df_bibliografia_asignatura:', df_bibliografia_asignatura.head())
print('df_profesores_asignaturas_total:', df_profesores_asignaturas_total.head())
print('df_titulaciones_escuelas_total:', df_titulaciones_escuelas_total.head())
print('df_titulaciones_asignaturas_total:', df_titulaciones_asignaturas_total.head())

###########################
###### POSTGRESQL ########
###########################
usuario = "userPSQL"
contraseña = "passPSQL"
host = "localhost"  
puerto = "5432"
base_datos = "postgres"

engine = create_engine(
    f"postgresql+psycopg2://{usuario}:{contraseña}@{host}:{puerto}/{base_datos}"
)

# Cargar DataFrame Asignaturas
df_asignaturas_total.to_sql('asignaturas', engine, if_exists="append", index=False)
df_titulaciones_total.to_sql('titulaciones', engine, if_exists="append", index=False)
df_escuelas_total.to_sql('escuelas', engine, if_exists="append", index=False)
df_titulaciones_asignaturas_total.to_sql('titulacionesasignaturas', engine, if_exists="append", index=False)
df_titulaciones_escuelas_total.to_sql('titulacionesescuelas', engine, if_exists="append", index=False)

# Cargar DataFrame Profesores
df_profesores_total = df_profesores_total.rename(columns={
    "Nombre": "nombre",
    "Correo electrónico": "correo_electronico"
})

df_profesores_total = df_profesores_total.reset_index().rename(columns={'index': 'id'})
df_profesores_total.to_sql('profesores', engine, if_exists="append", index=False)

# Cargar DataFrame Profesores - Asignaturas
df_profesores_asignaturas_total.to_sql('profesoresasignaturas', engine, if_exists="append", index=False)
                
# Cargar DataFrame Bibliografias
df_bibliografia_total['id'] = df_bibliografia_total.index
df_bibliografia_total.to_sql('bibliografias', engine, if_exists="append", index=False)

# Cargar DataFrame Bibliografias - Asignaturas
if not df_bibliografia_total.empty:
    df_bibliografia_asignatura = pd.merge(df_bibliografia_asignatura, df_bibliografia_total, on= "Nombre", how ="inner")
    df_bibliografia_asignatura = df_bibliografia_asignatura[["id","asignatura_id"]].rename(columns={"id": "bibliografia_id"}, inplace=True)
    df_bibliografia_asignatura.to_sql('bibliografiaasignaturas', engine, if_exists="append", index=False)

#############################################################################################################################################################################
# 2 - Contenidos de la asignatura                                                                                                                                           #
#############################################################################################################################################################################
directory = "Guias Docentes"
model = SentenceTransformer('distiluse-base-multilingual-cased-v2')

es = Elasticsearch("http://elasticsearch:9200")

index_name = "asignaturas_prueba"

mapping = {
    "mappings": {
        "properties": {
            "id_asignatura": {"type": "keyword"},

            "competencias": {
                "type": "nested",
                "properties": {
                    "codigo": {"type": "keyword"},
                    "texto": {"type": "text"}
                }
            },

            "competencias_vector":{
                "type": "dense_vector",
                "dims": 512,
                "index": True,
                "similarity": "cosine"
            },

            "descripcion_asignatura": {"type": "text"},

            "descripcion_vector":{
                "type": "dense_vector",
                "dims": 512,
                "index": True,
                "similarity": "cosine"
            },

            "temario": {
                "type": "nested",
                "properties": {
                    "numero": {"type": "keyword"},
                    "titulo": {"type": "text"},
                    "subtemas": {
                        "type": "nested",
                        "properties": {
                            "numero": {"type": "keyword"},
                            "titulo": {"type": "text"},
                        }
                    }
                }
            },
            
            "conocimientos_previos":  {"type": "text"},

            "conocimientos_previos_vector":{
                "type": "dense_vector",
                "dims": 512,
                "index": True,
                "similarity": "cosine"
            },

        }
    }
}
if not es.indices.exists(index=index_name):
    es.indices.create(index="vector_example", body=index_name)

documentos = []
for file in os.listdir(directory):
    if file.endswith(".pdf"):
        ruta = os.path.join(directory, file)
        df_asignatura = extract_asignatura(ruta)
        id_asignatura, nombre_asignatura = df_asignatura['Nombre de la asignatura'].values[0].split(" - ", maxsplit=1)
        
        ## Conocimientos previos recomendados
        conocimientos_previos, vector_conocimientos_previos = extraer_conocimientos_previos(ruta, model)

        # Competencias y resultados de aprendizaje
        ## Competencias de la asignatura
        competencias, vector_competencias = extraer_competencias(ruta, model)

        ## Resultados de aprendizaje
        resultados, vector_resultados = extraer_resultados_aprendizaje(ruta, model)

        # Descripción de la asignatura y temario
        ## Descripción de la asignatura
        descripcion_asignatura, vector_descripcion = extraer_descripcion_asignatura(ruta, model)

        ## Temario de la asignatura
        temario_estructurado = estructurar_temario(extraer_temario_asignatura(ruta))

        # Criterios de evaluación
        criterios_evaluacion = extraer_criterios_evaluacion(ruta)

        #############################################
        ################# INSERCIÓN #################
        #############################################
        documento = {
            "id_asignatura":id_asignatura,
            "competencias":competencias,
            "competencias_vector":vector_competencias,
            "descripcion_asignatura": descripcion_asignatura,
            "descripcion_vector": vector_descripcion,
            "temario":temario_estructurado,
            "conocimientos_previos": conocimientos_previos,
            "conocimientos_previos_vector": vector_conocimientos_previos,
        }
        documentos.append(documento)

bulk_index_data(es, documentos, index_name)
     