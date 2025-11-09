from sqlalchemy import create_engine, text
from rdflib import Graph, Literal, RDF, URIRef, Namespace, XSD
import requests


# === 1️⃣ Conexión a PostgreSQL con SQLAlchemy ===
usuario = "userPSQL"
contraseña = "passPSQL"
host = "localhost"  
puerto = "5432"
base_datos = "postgres"

engine = create_engine(
    f"postgresql+psycopg2://{usuario}:{contraseña}@{host}:{puerto}/{base_datos}"
)

# === 2️⃣ Espacios de nombres (namespaces) ===
UPM = Namespace("http://upm.es/ontology/")
DBO = Namespace("http://dbpedia.org/ontology/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

# === 3️⃣ Crear grafo RDF ===
g = Graph()
g.bind("upm", UPM)
g.bind("dbo", DBO)
g.bind("foaf", FOAF)

# === 4️⃣ Función auxiliar para URIs ===
def uri(base, tipo, id):
    return URIRef(f"{base}{tipo}/{id}")

# === 5️⃣ Mapeos: Tablas → Clases RDF ===
with engine.connect() as conn:

    ### Escuelas ###
    result = conn.execute(text("SELECT id, nombre, entidad_dbpedia FROM Escuelas;"))
    for id, nombre, entidad in result:
        escuela_uri = uri(UPM, "Escuela", id)
        g.add((escuela_uri, RDF.type, UPM.Escuela))
        g.add((escuela_uri, UPM.nombre, Literal(nombre, datatype=XSD.string)))
        g.add((escuela_uri, UPM.codigo, Literal(id, datatype=XSD.integer)))
        if entidad:
            g.add((escuela_uri, UPM.entidad_dbpedia, Literal(entidad, datatype=XSD.string)))

    ### Titulaciones ###
    result = conn.execute(text("SELECT id, nombre, tipo_estudio FROM Titulaciones;"))
    for id, nombre, tipo in result:
        tit_uri = uri(UPM, "Titulacion", id)
        g.add((tit_uri, RDF.type, UPM.Titulacion))
        g.add((tit_uri, UPM.nombre, Literal(nombre, datatype=XSD.string)))
        g.add((tit_uri, UPM.codigoTitulacion, Literal(id, datatype=XSD.string)))
        g.add((tit_uri, UPM.tipo, Literal(tipo, datatype=XSD.string)))

    ### Asignaturas ###
    result = conn.execute(text("""
        SELECT id, nombre, numero_creditos, semestre, idioma
        FROM Asignaturas;
    """))
    for (id, nombre, creditos, semestre, idioma) in result:
        asig_uri = uri(UPM, "Asignatura", id)
        g.add((asig_uri, RDF.type, UPM.Asignatura))
        g.add((asig_uri, UPM.nombre, Literal(nombre, datatype=XSD.string)))
        g.add((asig_uri, UPM.creditosECTS, Literal(creditos, datatype=XSD.integer)))
        if semestre: g.add((asig_uri, UPM.semestre, Literal(semestre, datatype=XSD.string)))
        if idioma: g.add((asig_uri, UPM.idioma, Literal(idioma, datatype=XSD.string)))

    ### Profesores ###
    result = conn.execute(text("SELECT id, nombre, correo_electronico FROM Profesores;"))
    for id, nombre, correo in result:
        prof_uri = uri(UPM, "Profesor", id)
        g.add((prof_uri, RDF.type, UPM.Profesor))
        g.add((prof_uri, UPM.nombre, Literal(nombre, datatype=XSD.string)))
        g.add((prof_uri, UPM.correo, Literal(correo, datatype=XSD.string)))

    ### Recursos bibliográficos ###
    result = conn.execute(text("SELECT id, nombre, autores, direccion_url FROM Bibliografias;"))
    for id, titulo, autor, url in result:
        rec_uri = uri(UPM, "RecursoBibliografico", id)
        g.add((rec_uri, RDF.type, UPM.RecursoBibliografico))
        g.add((rec_uri, UPM.titulo, Literal(titulo, datatype=XSD.string)))
        g.add((rec_uri, UPM.autor, Literal(autor, datatype=XSD.string)))
        if url:
            g.add((rec_uri, UPM.direccionURL, Literal(url, datatype=XSD.string)))

    ### Relaciones Titulaciones ↔ Escuelas ###
    result = conn.execute(text("SELECT titulacion_id, escuela_id FROM TitulacionesEscuelas;"))
    for tit_id, esc_id in result:
        g.add((uri(UPM, "Escuela", esc_id), UPM.imparteTitulacion, uri(UPM, "Titulacion", tit_id)))

    ### Relaciones Titulaciones ↔ Asignaturas ###
    result = conn.execute(text("SELECT titulacion_id, asignatura_id FROM TitulacionesAsignaturas;"))
    for tit_id, asig_id in result:
        g.add((uri(UPM, "Titulacion", tit_id), UPM.incluyeAsignatura, uri(UPM, "Asignatura", asig_id)))

    ### Relaciones Asignaturas ↔ Profesores ###
    result = conn.execute(text("SELECT asignatura_id, profesor_id FROM ProfesoresAsignaturas;"))
    for asig_id, prof_id in result:
        g.add((uri(UPM, "Asignatura", asig_id), UPM.tieneProfesor, uri(UPM, "Profesor", prof_id)))

all_triples = []
for s, p, o in g:
    triple_ttl = f"<{s}> <{p}> "
    if isinstance(o, URIRef):
        triple_ttl += f"<{o}> ."
    else:
        triple_ttl += f"\"\"\"{o}\"\"\" ."
    all_triples.append(triple_ttl)

batch_size = 20
for i in range(0, len(all_triples), batch_size):
    batch = all_triples[i:i + batch_size]
    sparql_update = "INSERT DATA { " + "\n".join(batch) + " }"

    r = requests.post(
        f"http://localhost:8000/repositories/asignaturas/statements",
        data={"update": sparql_update},
        auth=None
    )

    if r.status_code != 204:
        print("❌ Error subiendo batch:", r.status_code, r.text)
    else:
        print(f"✅ Batch {i//batch_size + 1} subido correctamente ({len(batch)} triples)")