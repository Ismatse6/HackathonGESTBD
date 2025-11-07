# datos de la asignatura: me falta la url de la guia docente y el coordinador de la asignatura

from pathlib import Path
import pdfplumber
import pandas as pd
import re
import os
import sys
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy.orm import sessionmaker
from models import Base, Asignatura, Titulacion, Escuela, Profesor, TitulacionesEscuelas, ProfesoresAsignaturas
from sqlalchemy import create_engine

#pdf_path = "./GA_61AH_613000129_1S_2025-26.pdf"
#pdf_path = "./GA_61AH_613000133_2S_2025-26.pdf"

def extraer_datos_asignatura(pdf_path:str, titulo_regex=r"1\.1\.\s*Datos\s+de\s+la\s+asignatura"):
    """
    Busca el título en la página, recorta el área bajo el título y extrae la primera tabla.
    Devuelve un DataFrame (una fila con todas las claves/valores).
    """
    pdf_path = Path(pdf_path)
    assert pdf_path.exists(), f"No existe: {pdf_path}"

    with pdfplumber.open(pdf_path) as pdf:
        for pnum, page in enumerate(pdf.pages, start=1):
            # Detectar si el título está en esta página (texto normalizado)
            text = page.extract_text() or ""
            if not re.search(titulo_regex, text, flags=re.IGNORECASE):
                continue

            # Obtener posición Y del título usando palabras (para recortar por debajo)
            words = page.extract_words(use_text_flow=True, keep_blank_chars=False)
            # Normalizamos palabras
            tokens = [w["text"] for w in words]
            norm_tokens = [re.sub(r"\s+", " ", t.strip()) for t in tokens]
            joined = " ".join(norm_tokens)

            # Si falla exacto, buscar por palabras clave
            titulo_palabras = ["1.1.", "Datos", "de", "la", "asignatura"]
            idxs = []
            for i, w in enumerate(words):
                if re.sub(r"\W+", "", w["text"].lower()) == "1" or w["text"] == "1.1.":
                    idxs.append(i)

            header_bottom = None
            # emparejar secuencia exacta
            lowered = [re.sub(r"\W+", "", w["text"].lower()) for w in words]
            needle = [re.sub(r"\W+", "", s.lower()) for s in titulo_palabras]
            for i in range(len(lowered) - len(needle) + 1):
                if lowered[i:i+len(needle)] == needle:
                    header_bottom = max(words[i + len(needle) - 1]["bottom"], words[i]["bottom"])
                    break

            # Si no se ha encontrado la secuencia, recurre a buscar "1.1." y "asignatura" en la misma línea aproximada
            if header_bottom is None and words:
                line_groups = {}
                for w in words:
                    # Agrupar por línea aproximada usando 'top'
                    key = round(w["top"] / 3)
                    line_groups.setdefault(key, []).append(w)
                for line in line_groups.values():
                    texto_linea = " ".join([x["text"] for x in sorted(line, key=lambda z: z["x0"])])
                    if re.search(titulo_regex, texto_linea, flags=re.IGNORECASE):
                        header_bottom = max([x["bottom"] for x in line])
                        break

            # Si no se encuentra la posición, aun así prueba toda la página
            crop_top = (header_bottom + 4) if header_bottom else 0

            # Recortar área por debajo del título y extraer tablas
            region = page.crop((0, crop_top, page.width, page.height))
            tablas = region.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "intersection_tolerance": 5,
            })
            if not tablas:
                tablas = region.extract_tables({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                })

            if not tablas:
                continue  # prueba en otra página por si el título se repite y la tabla está después

            # Tomar la primera tabla "buena" y la limpiamos
            from itertools import dropwhile
            for t in tablas:
                df = pd.DataFrame(t)
                # quitar filas separadoras '----'
                df = df[~df.iloc[:,0].fillna("").str.contains(r"^-{3,}$")]
                # si la primera fila son encabezados
                if df.shape[0] > 1 and all(isinstance(x, str) for x in df.iloc[0].tolist()):
                    # Si parece tabla clave-valor (2 columnas)
                    if df.shape[1] > 2:
                        df.columns = df.iloc[0].fillna("").tolist()
                        df = df.drop(index=df.index[0]).reset_index(drop=True)

                # Caso típico: 2 columnas (clave | valor)
                if df.shape[1] == 2:
                    df = df.rename(columns={df.columns[0]: "clave", df.columns[1]: "valor"})
                    # Filas totalmente vacías fuera
                    df = df.dropna(how="all").applymap(lambda x: x.strip() if isinstance(x, str) else x)
                    # Convertir a DataFrame de una sola fila con todas las claves
                    kv = dict(zip(df["clave"], df["valor"]))
                    resultado = pd.DataFrame([kv])
                else:
                    # Si viniera como más columnas, se deja tal cual
                    resultado = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

                return resultado  # se ha encontrado la tabla

    raise ValueError("No se pudo localizar la tabla de '1.1. Datos de la asignatura' en el PDF.")

def main():
    if len(sys.argv) < 2:
        print("Uso: python extraccion_asignatura.py <ruta_fichero_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    df_asignatura = extraer_datos_asignatura(pdf_path)
    #df_asignatura.to_csv("datos_asignatura_extraidos.csv", index=False)

    id_asignatura, nombre_asignatura = df_asignatura['Nombre de la asignatura'].values[0].split(" - ", maxsplit=1)
    num_creditos = df_asignatura['No de créditos'].values[0].split(" ")[0]
    curso_texto = df_asignatura['Curso'].values[0]
    semestre_texto = df_asignatura['Semestre'].values[0]
    idioma = df_asignatura['Idioma de impartición'].values[0]
    plan_estudios, nombre_titulacion = df_asignatura['Titulación'].values[0].split(" - ", maxsplit=1)
    nombre_escuela = df_asignatura['Centro responsable de la\ntitulación'].values[0].split(" - ", maxsplit=1)[1]
    curso_academico = df_asignatura['Curso académico'].values[0]

    """
    print(f"ID Asignatura: {id_asignatura}")
    print(f"Nombre Asignatura: {nombre_asignatura}")
    print(f"Créditos: {num_creditos}")
    print(f"Curso: {curso_texto}")
    print(f"Semestre: {semestre_texto}")
    print(f"Idioma: {idioma}")
    print(f"Titulación: {nombre_titulacion}")
    print(f"Escuela: {nombre_escuela}")
    print(f"Curso académico: {curso_academico}")
    """

    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")

    DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    engine = create_engine(DATABASE_URL, echo=True, future=True)

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    with Session() as session:
        escuela = session.query(Escuela).filter_by(nombre=nombre_escuela).first()
        print('Escuela encontrada:', escuela)
        if not escuela:
            print('Creando escuela')
            escuela = Escuela(
                nombre=nombre_escuela,
                direccion="Desconocida",
                direccion_url="Desconocida"
            )
            session.add(escuela)
            session.commit()
        
        titulacion = session.query(Titulacion).filter_by(nombre=nombre_titulacion).first()
        print('Titulacion encontrada:', titulacion)
        if not titulacion:
            print('Creando titulacion')
            titulacion = Titulacion(
                nombre=nombre_titulacion,
                tipo_estudio="Desconocido",
                plan_estudios=plan_estudios
            )
            session.add(titulacion)
            session.commit()

        profesor = session.query(Profesor).filter_by(nombre="Desconocido").first()
        if not profesor:
            profesor = Profesor(
                nombre="Desconocido",
                correo_electronico="Desconocido",
                categoria_academica="Desconocido"
            )
            session.add(profesor)
            session.commit()

        
        nueva_asignatura = Asignatura(
            nombre=nombre_asignatura,
            coordinador="Desconocido",
            numero_creditos=num_creditos,
            agno_academico=curso_academico,
            direccion_url="Desconocida",
            semestre=semestre_texto,
            idioma=idioma,
            id_guia_docente=id_asignatura,
            titulacion_obj=titulacion,
        )
        nueva_asignatura.profesores.append(profesor)
        print('añadiendo la asignatura')
        session.add(nueva_asignatura)
        session.commit()

if __name__ == "__main__":
    main()