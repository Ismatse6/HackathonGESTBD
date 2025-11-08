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

#############################################################################################################################################################################
# 2 - Contenidos de la asignatura                                                                                                                                           #
#############################################################################################################################################################################
directory = "Guias Docentes"
model = SentenceTransformer('distiluse-base-multilingual-cased-v2')

es = Elasticsearch("http://localhost:9200")

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

            "resultados": {
                "type": "nested",
                "properties": {
                    "codigo": {"type": "keyword"},
                    "texto": {"type": "text"},
                }
            },

            "resultados_vector":{
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


        }
    }
}
if not es.indices.exists(index=index_name):
    es.indices.create(index="vector_example", body=index_name)

documentos = []
for file in os.listdir(directory):
    if file.endswith(".pdf"):
        ruta = os.path.join(directory, file)

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
            "id_asignatura":1,
            "competencias":competencias,
            "competencias_vector":vector_competencias,
            "resultados": resultados,
            "resultados_vector": vector_resultados,
            "descripcion_asignatura": descripcion_asignatura,
            "descripcion_vector": vector_descripcion
        }
        documentos.append(documento)

bulk_index_data(es, documentos, index_name)
     