import pandas as pd
import os
import random
import time
import requests
from utils import (
    extract_asignatura,
    scrapBibliography,
    scrapGoogleScholar,
    extraer_competencias,
    extraer_conocimientos_previos,
    scrapProfesores,
    estructurar_temario,
    extraer_descripcion_asignatura,
    extraer_temario_asignatura,
    bulk_index_data,
    uri,
    doc_to_triples
)
from elasticsearch import Elasticsearch
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
from rdflib import Graph, Literal, RDF, URIRef, Namespace, XSD

# Variables iniciales
directory = "Guias Docentes"

model = SentenceTransformer('distiluse-base-multilingual-cased-v2')

df_bibliografia_total = pd.DataFrame()
df_bibliografia_asignatura = pd.DataFrame()
df_profesores_total = pd.DataFrame()
df_profesores_asignaturas_total = pd.DataFrame()
df_asignaturas_total = pd.DataFrame()
df_escuelas_total = pd.DataFrame()
df_titulaciones_total = pd.DataFrame()
df_titulaciones_escuelas_total = pd.DataFrame()
df_titulaciones_asignaturas_total = pd.DataFrame()

error_bibliografias = False

documentos = []

################################
# Paso 1: Extrarer informacion #
################################
for file in os.listdir(directory):
    if file.endswith(".pdf"):  
        pdf_path = os.path.join(directory, file)
        #############
        # Metadatos #
        #############

        # Asignatura
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
        
        # Titulaciones 
        df_asignaturas_total = pd.concat([df_asignaturas_total, df_asignatura], ignore_index=True)
        if df_titulaciones_total.empty or plan_estudios not in df_titulaciones_total['id'].values:
            df_titulacion = pd.DataFrame([{
                "id": plan_estudios,
                "nombre": nombre_titulacion,
                "tipo_estudio": "Grado" if "Grado" in nombre_titulacion else "Máster"
            }])
            df_titulaciones_total = pd.concat([df_titulaciones_total, df_titulacion], ignore_index=True)

        # Escuelas
        if df_escuelas_total.empty or id_escuela not in df_escuelas_total['id'].values:
            df_escuela = pd.DataFrame([{
                "id": id_escuela,
                "nombre": nombre_escuela,
                "entidad_dbpedia": "http://es.dbpedia.org/resource/Escuela_Técnica_Superior_de_Ingeniería_de_Sistemas_Informáticos_(Universidad_Politécnica_de_Madrid)"
            }])
            df_escuelas_total = pd.concat([df_escuelas_total, df_escuela], ignore_index=True)
        
        # Escuelas - Titulaciones
        if df_titulaciones_escuelas_total.empty or df_titulaciones_escuelas_total.get((df_titulaciones_escuelas_total['titulacion_id'] == plan_estudios) & (df_titulaciones_escuelas_total['escuela_id'] == id_escuela)).any().any() == False:
            df_titulacion_escuela = pd.DataFrame([{
                "titulacion_id": plan_estudios,
                "escuela_id": id_escuela
            }])
            df_titulaciones_escuelas_total = pd.concat([df_titulaciones_escuelas_total, df_titulacion_escuela], ignore_index=True)
        
        # Titulaciones -Asignatura
        df_titulacion_asignatura = pd.DataFrame([{
            "titulacion_id": plan_estudios,
            "asignatura_id": id_asignatura
        }])
        df_titulaciones_asignaturas_total = pd.concat([df_titulaciones_asignaturas_total, df_titulacion_asignatura], ignore_index=True)
        
        # Bibliografia
        if not error_bibliografias:
            df_scrap_bibliografia = scrapBibliography(pdf_path, {"nombre", "tipo", "observaciones"})  
            dfs_bibliografia = []
            for nombre in df_scrap_bibliografia['Nombre']:
                try:
                    dict_bibliografia = scrapGoogleScholar(nombre)
                    if dict_bibliografia and "Titulo" in dict_bibliografia:
                        df_bibliografia = pd.DataFrame([dict_bibliografia])
                        dfs_bibliografia.append(df_bibliografia)
                except Exception as e:
                    print(f"Error con {nombre}: {e}")
                    error_bibliografias = True
                    break
                time.sleep(random.uniform(5, 20))

            if dfs_bibliografia:
                df_bibliografia = pd.concat(dfs_bibliografia, ignore_index=True)
                df_bibliografia_total =  pd.concat([df_bibliografia_total, df_bibliografia], ignore_index=True).drop_duplicates(subset=["Titulo"])
                list_bibliografias = df_bibliografia_total['Titulo'].dropna().unique()
                df_bibliografia_asignatura = pd.concat([df_bibliografia_asignatura,pd.DataFrame({'Titulo':list_bibliografias, 'id_asignatura': [id_asignatura]*len(list_bibliografias)})])
        
        
        # Profesores
        df_profesores = scrapProfesores(pdf_path, {"nombre", "correo electrónico"})
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
        
        print(f"Metadatos descargados para el archivo {nombre_asignatura}")

        #############
        # Contenido #
        #############

        # Contenidos previos
        conocimientos_previos, vector_conocimientos_previos = extraer_conocimientos_previos(pdf_path, model)

        # Competencias 
        competencias, vector_competencias = extraer_competencias(pdf_path, model)

        # Descripcion
        descripcion_asignatura, vector_descripcion = extraer_descripcion_asignatura(pdf_path, model)

        # Temario
        temario_estructurado = estructurar_temario(extraer_temario_asignatura(pdf_path))

        documento = {
            "id_asignatura":id_asignatura,
            "nombre_asignatura": nombre_asignatura,
            "competencias":competencias,
            "competencias_vector":vector_competencias,
            "descripcion_asignatura": descripcion_asignatura,
            "descripcion_vector": vector_descripcion,
            "temario":temario_estructurado,
            "conocimientos_previos": conocimientos_previos,
            "conocimientos_previos_vector": vector_conocimientos_previos,
        }
        documentos.append(documento)
        print(f"Contenido descargado  para el archivo {nombre_asignatura}")

print("Datos descargados")

#################################
# Paso 2: Almacenar informacion #
#################################

# Almacenar Metadatos -> PostGreSQL
usuario = "userPSQL"
contraseña = "passPSQL"
host = "localhost"  
puerto = "5432"
base_datos = "postgres"

engine = create_engine(f"postgresql+psycopg2://{usuario}:{contraseña}@{host}:{puerto}/{base_datos}")

# Cargar DataFrame Asignaturas
df_asignaturas_total.to_sql('asignaturas', engine, if_exists="append", index=False)
#df_asignaturas_total.to_csv('df_asignaturas_total.csv')

# Cargar DataFrame Titulaciones
df_titulaciones_total.to_sql('titulaciones', engine, if_exists="append", index=False)
#df_titulaciones_total.to_csv('df_titulaciones_total.csv')

# Cargar DataFrame Escuelas
df_escuelas_total.to_sql('escuelas', engine, if_exists="append", index=False)
#df_escuelas_total.to_csv('df_escuelas_total.csv')

# Cargar DataFrame Titulaciones - Asignaturas
df_titulaciones_asignaturas_total.to_sql('titulacionesasignaturas', engine, if_exists="append", index=False)
#df_titulaciones_asignaturas_total.to_csv('df_titulaciones_asignaturas_total.csv')

# Cargar DataFrame Titulaciones - Escuelas
df_titulaciones_escuelas_total.to_sql('titulacionesescuelas', engine, if_exists="append", index=False)
#df_titulaciones_escuelas_total.to_csv('df_titulaciones_escuelas_total.csv')

# Cargar DataFrame Profesores
df_profesores_total = df_profesores_total.rename(columns={
    "Nombre": "nombre",
    "Correo electrónico": "correo_electronico"
})
df_profesores_total = df_profesores_total.reset_index().rename(columns={'index': 'id'})
df_profesores_total.to_sql('profesores', engine, if_exists="append", index=False)
#df_profesores_total.to_csv('df_profesores_total.csv')

# Cargar DataFrame Profesores - Asignaturas
df_profesores_asignaturas_total.to_sql('profesoresasignaturas', engine, if_exists="append", index=False)
#df_profesores_asignaturas_total.to_csv('df_profesores_asignaturas_total.csv')
              
# Cargar DataFrame Bibliografias
df_bibliografia_total['id'] = df_bibliografia_total.index
df_bibliografia_total.to_sql('bibliografias', engine, if_exists="append", index=False)
#df_bibliografia_total.to_csv('df_bibliografia_total.csv')

# Cargar DataFrame Bibliografias - Asignaturas
if not df_bibliografia_total.empty:
    df_bibliografia_asignatura = pd.merge(df_bibliografia_asignatura, df_bibliografia_total, on= "Titulo", how ="inner")
    df_bibliografia_asignatura = df_bibliografia_asignatura[["id", "id_asignatura"]].rename(columns={"id": "bibliografia_id"})    
    df_bibliografia_asignatura.to_sql('bibliografiaasignaturas', engine, if_exists="append", index=False)
    #df_bibliografia_asignatura.to_csv('df_bibliografia_asignatura.csv')

# Almacenar Contenido -> ElasticSearch
es = Elasticsearch("http://localhost:9200")

index_name = "guias_docentes"

mapping = {
    "mappings": {
        "properties": {
            "id_asignatura": {"type": "keyword"},

            "nombre_asignatura": {"type": "text"},

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
    es.indices.create(index=index_name, body=mapping)
bulk_index_data(es, documentos, index_name)

print("Datos almacenados")

###############################
# Paso 2: Enlazar informacion #
###############################

UPM = Namespace("http://upm.es/ontology/")
DBO = Namespace("http://dbpedia.org/ontology/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
graphdb_repo = "http://localhost:8000/repositories/asignaturas/statements"

g = Graph()
g.bind("upm", UPM)
g.bind("dbo", DBO)
g.bind("foaf", FOAF)

with engine.connect() as conn:
    # Escuelas
    result = conn.execute(text("SELECT id, nombre, entidad_dbpedia FROM Escuelas;"))
    for id, nombre, entidad in result:
        escuela_uri = uri(UPM, "Escuela", id)
        g.add((escuela_uri, RDF.type, UPM.Escuela))
        g.add((escuela_uri, UPM.nombre, Literal(nombre, datatype=XSD.string)))
        g.add((escuela_uri, UPM.codigo, Literal(id, datatype=XSD.integer)))
        if entidad:
            g.add((escuela_uri, UPM.entidad_dbpedia, URIRef(entidad)))

    # Titulaciones
    result = conn.execute(text("SELECT id, nombre, tipo_estudio FROM Titulaciones;"))
    for id, nombre, tipo in result:
        tit_uri = uri(UPM, "Titulacion", id)
        g.add((tit_uri, RDF.type, UPM.Titulacion))
        g.add((tit_uri, UPM.nombre, Literal(nombre, datatype=XSD.string)))
        g.add((tit_uri, UPM.codigoTitulacion, Literal(id, datatype=XSD.string)))
        g.add((tit_uri, UPM.tipo, Literal(tipo, datatype=XSD.string)))

    # Asignaturas 
    result = conn.execute(text("SELECT id, nombre, numero_creditos, semestre, idioma FROM Asignaturas;"))
    for (id, nombre, creditos, semestre, idioma) in result:
        asig_uri = uri(UPM, "Asignatura", id)
        g.add((asig_uri, RDF.type, UPM.Asignatura))
        g.add((asig_uri, UPM.nombre, Literal(nombre, datatype=XSD.string)))
        g.add((asig_uri, UPM.creditosECTS, Literal(creditos, datatype=XSD.integer)))
        if semestre: g.add((asig_uri, UPM.semestre, Literal(semestre, datatype=XSD.string)))
        if idioma: g.add((asig_uri, UPM.idioma, Literal(idioma, datatype=XSD.string)))

    # Profesores
    result = conn.execute(text("SELECT id, nombre, correo_electronico FROM Profesores;"))
    for id, nombre, correo in result:
        prof_uri = uri(UPM, "Profesor", id)
        g.add((prof_uri, RDF.type, UPM.Profesor))
        g.add((prof_uri, UPM.nombre, Literal(nombre, datatype=XSD.string)))
        g.add((prof_uri, UPM.correo, Literal(correo, datatype=XSD.string)))

    # Recursos bibliográficos 
    result = conn.execute(text("SELECT * FROM Bibliografias;"))
    for id, titulo, autor, url in result:
        rec_uri = uri(UPM, "RecursoBibliografico", id)
        g.add((rec_uri, RDF.type, UPM.RecursoBibliografico))
        g.add((rec_uri, UPM.titulo, Literal(titulo, datatype=XSD.string)))
        g.add((rec_uri, UPM.autor, Literal(autor, datatype=XSD.string)))
        if url:
            g.add((rec_uri, UPM.direccionURL, Literal(url, datatype=XSD.string)))

    # Relaciones Titulaciones ↔ Escuelas 
    result = conn.execute(text("SELECT titulacion_id, escuela_id FROM TitulacionesEscuelas;"))
    for tit_id, esc_id in result:
        g.add((uri(UPM, "Escuela", esc_id), UPM.imparteTitulacion, uri(UPM, "Titulacion", tit_id)))

    # Relaciones Titulaciones ↔ Asignaturas 
    result = conn.execute(text("SELECT titulacion_id, asignatura_id FROM TitulacionesAsignaturas;"))
    for tit_id, asig_id in result:
        g.add((uri(UPM, "Titulacion", tit_id), UPM.incluyeAsignatura, uri(UPM, "Asignatura", asig_id)))

    # Relaciones Asignaturas ↔ Profesores 
    result = conn.execute(text("SELECT asignatura_id, profesor_id FROM ProfesoresAsignaturas;"))
    for asig_id, prof_id in result:
        g.add((uri(UPM, "Asignatura", asig_id), UPM.tieneProfesor, uri(UPM, "Profesor", prof_id)))

    """# Relaciones Asignaturas ↔ Bibliografias 
    result = conn.execute(text("SELECT * FROM BibliografiasAsignaturas;"))
    for asig_id, bib_id in result:
        g.add((uri(UPM, "Asignatura", asig_id), UPM.tieneRecursoBibliografico, uri(UPM, "RecursoBibliografico", bib_id)))"""

all_triples = []
for s, p, o in g:
    triple_ttl = f"<{s}> <{p}> "
    if isinstance(o, URIRef):
        triple_ttl += f"<{o}> ."
    else:
        triple_ttl += f"\"\"\"{o}\"\"\" ."
    all_triples.append(triple_ttl)

query = {"match_all": {}}
res = es.search(index=index_name, query=query, size=1000)
for hit in res['hits']['hits']:
    doc = hit['_source']
    all_triples.extend(doc_to_triples(doc))

batch_size = 50
for i in range(0, len(all_triples), batch_size):
    batch = all_triples[i:i + batch_size]
    sparql_update = "INSERT DATA { " + "\n".join(batch) + " }"
    r = requests.post(
        graphdb_repo,
        data={"update": sparql_update},
        auth=None
    )
    if r.status_code != 204:
        print("Error subiendo batch:", r.status_code, r.text)
    else:
        print(f"Batch {i//batch_size + 1} subido correctamente ({len(batch)} triples)")

print("Datos enlazados")