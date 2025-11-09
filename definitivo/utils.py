import pdfplumber
import pandas as pd
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import quote
from pathlib import Path
import re


######################
# Funciones Pipeline #
######################

def hasTargetHeaders(tabla, encabezados_objetivo):
    """
    Verifica si la primera fila de una tabla PDF contiene todos los encabezados esperados.

    Parámetros:
        tabla (list[list[str]]): Lista de filas (cada fila es una lista de celdas).
        encabezados_objetivo (set[str]): Conjunto de encabezados requeridos (en minúsculas).

    Retorna:
        bool: True si la tabla contiene todos los encabezados buscados, False en caso contrario.
    """
    if not tabla or len(tabla) == 0:
        return False
    encabezados = [str(celda).strip().lower() for celda in tabla[0] if celda]
    return encabezados_objetivo.issubset(set(encabezados))


def extract_asignatura(pdf_path:str, titulo_regex=r"1\.1\.\s*Datos\s+de\s+la\s+asignatura"):
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

def scrapBibliography(ruta, encabezados_objetivo):
    """
    Extrae una tabla específica desde un PDF que contiene los encabezados objetivo.

    Parámetros:
        ruta (str): Ruta del archivo PDF.
        encabezados_objetivo (set[str]): Encabezados que identifican la tabla buscada.

    Retorna:
        pandas.DataFrame: Tabla encontrada, limpiada y combinada si se extiende en varias páginas.
    """
    tablas_por_pagina = []

    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            tablas_pagina = []
            for tabla in pagina.extract_tables():
                if tabla and len(tabla) > 1:
                    tablas_pagina.append(tabla)
            tablas_por_pagina.append(tablas_pagina)

    tabla_encontrada = None
    indice_pagina = -1
    indice_tabla = -1

    for i, tablas_pag in enumerate(tablas_por_pagina):
        for j, tabla in enumerate(tablas_pag):
            if hasTargetHeaders(tabla, encabezados_objetivo):
                tabla_encontrada = tabla
                indice_pagina = i
                indice_tabla = j
                break
        if tabla_encontrada:
            break
    
    if not tabla_encontrada:
        return pd.DataFrame()  

    filas_combinadas = list(tabla_encontrada)
    pagina_actual = indice_pagina

    while True:
        tablas_pag_actual = tablas_por_pagina[pagina_actual]

        if indice_tabla != len(tablas_pag_actual) - 1:
            break

        if pagina_actual + 1 >= len(tablas_por_pagina):
            break

        tablas_pag_siguiente = tablas_por_pagina[pagina_actual + 1]
        if not tablas_pag_siguiente:
            break

        primera_tabla_siguiente = tablas_pag_siguiente[0]

        if hasTargetHeaders(primera_tabla_siguiente, encabezados_objetivo):
            break

        filas_combinadas.extend(primera_tabla_siguiente)
        pagina_actual += 1
        indice_tabla = 0

    df = pd.DataFrame(filas_combinadas[1:], columns=filas_combinadas[0])

    df = df[~df["Nombre"].str.contains(r"^https?://", na=False)]
    df = df[df["Tipo"] == "Bibliografía"]

    df["Nombre"] = df["Nombre"].str.replace("\n", " ", regex=False)
    df["Observaciones"] = df["Observaciones"].str.replace("\n", " ", regex=False)

    return df

def scrapGoogleScholar(name):
    """
    Busca un autor o título en Google Scholar y devuelve información básica del primer resultado.

    Parámetros:
        name (str): Nombre del autor o texto a buscar.

    Retorna:
        dict: Contiene título, autores y enlace del primer resultado encontrado.
    """
    url = f"https://scholar.google.com/scholar?q={quote(name)}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    respuesta = requests.get(url, headers=headers)

    if respuesta.status_code != 200:
        raise Exception(f"Error al acceder a Google Scholar: {respuesta.status_code}")

    soup = BeautifulSoup(respuesta.text, "html.parser")
    resultado = {}
    item = soup.select_one(".gs_r.gs_or.gs_scl")

    if item:
        titulo_elem = item.select_one(".gs_rt")
        autor_elem = item.select_one(".gs_a")
        link_elem = titulo_elem.find("a") if titulo_elem else None

        titulo = titulo_elem.get_text(strip=True) if titulo_elem else ""
        autores = autor_elem.get_text(strip=True) if autor_elem else ""
        enlace = link_elem["href"] if link_elem and link_elem.has_attr("href") else ""

        for tag in ["[PDF]", "[LIBRO]", "[B]", "[CITAS]", "[C]", "[HTML]"]:
            titulo = titulo.replace(tag, "")

        resultado["Titulo"] = titulo.strip()
        resultado["Autores"] = autores.split("-")[0].strip()
        resultado["Enlace"] = enlace

    return resultado

def extraer_texto_limpio(ruta_pdf, margen_superior=60, margen_inferior=60):
    """
    Extrae el texto completo de un PDF eliminando encabezados y pies de página, recortando por posición física en el PDF.
    Devuelve también las páginas recortadas como objetos pdfplumber.Page.

    Parámetros:
        ruta_pdf (str): Ruta del archivo PDF.
        margen_superior (int): Altura en puntos a recortar desde la parte superior.
        margen_inferior (int): Altura en puntos a recortar desde la parte inferior.

    Devuelve:
        tuple[str, list]: Texto limpio y lista de páginas recortadas (pdfplumber.Page)
    """
    texto_limpio = ""
    paginas_recortadas = []

    with pdfplumber.open(ruta_pdf) as pdf:
        for page in pdf.pages:
            y0, y1 = margen_inferior, page.height - margen_superior
            area_util = (0, y0, page.width, y1)
            recorte = page.within_bbox(area_util)
            paginas_recortadas.append(recorte)
            texto = recorte.extract_text()
            if texto:
                texto_limpio += texto + "\n"

    return texto_limpio, paginas_recortadas


def scrapProfesores(ruta, encabezados_objetivo):
    # Extraer tablas por página
    tablas_por_pagina = []
    
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            tablas_pagina = []
            for tabla in pagina.extract_tables():
                if tabla and len(tabla) > 1:  
                    tablas_pagina.append(tabla)
            tablas_por_pagina.append(tablas_pagina)



    # Buscar la tabla con los encabezados objetivo
    tabla_encontrada = None
    indice_pagina = -1
    indice_tabla = -1

    for i, tablas_pag in enumerate(tablas_por_pagina):
        for j, tabla in enumerate(tablas_pag):
            if hasTargetHeaders(tabla, encabezados_objetivo):
                tabla_encontrada = tabla
                indice_pagina = i
                indice_tabla = j
                break
        if tabla_encontrada:
            break

    if not tabla_encontrada:
        return pd.DataFrame()

    # Combinar con tablas de páginas siguientes si es necesario
    filas_combinadas = list(tabla_encontrada)
    pagina_actual = indice_pagina

    while True:
        tablas_pag_actual = tablas_por_pagina[pagina_actual]
        
        # Verificar si la tabla actual es la última de la página
        if indice_tabla != len(tablas_pag_actual) - 1:
            # No es la última tabla de la página, terminar
            break
        
        # Verificar si hay una página siguiente
        if pagina_actual + 1 >= len(tablas_por_pagina):
            # No hay más páginas, terminar
            break
        
        # Verificar si la página siguiente tiene tablas
        tablas_pag_siguiente = tablas_por_pagina[pagina_actual + 1]
        if not tablas_pag_siguiente:
            # No hay tablas en la siguiente página, terminar
            break
        
        # Obtener la primera tabla de la página siguiente
        primera_tabla_siguiente = tablas_pag_siguiente[0]
        
        # Verificar si la primera tabla de la siguiente página tiene encabezados
        if hasTargetHeaders(primera_tabla_siguiente, encabezados_objetivo):
            # Tiene encabezados, no combinar
            break
        
        # Combinar: agregar las filas de la primera tabla de la siguiente página
        # (sin incluir la primera fila si parece un encabezado)
        filas_combinadas.extend(primera_tabla_siguiente)
        
        # Actualizar para la siguiente iteración
        pagina_actual += 1
        indice_tabla = 0

    # Crear DataFrame con las filas combinadas
    df = pd.DataFrame(filas_combinadas[1:], columns=filas_combinadas[0])
    df["Nombre"] = df["Nombre"].str.split("\n").str[0]
    df = df[~df["Nombre"].str.contains(r"^https?://", na=False)]
    
    return df[["Nombre", "Correo electrónico"]] 

def extraer_seccion(ruta_pdf, titulo=None, inicio=None, fin=None):
    """
    Extrae una sección genérica de una guía en PDF usando pdfplumber.

    Parámetros:
        ruta_pdf (str): Ruta del archivo PDF.
        titulo (str): Título principal de la sección (ej. 'Descripción de la asignatura y temario').
        inicio (str): Subtítulo o punto de inicio del bloque (ej. 'Descripción de la asignatura').
        fin (str): Subtítulo o punto final del bloque (ej. 'Temario de la asignatura').

    Devuelve:
        str: Texto extraído entre los límites indicados, o el texto más cercano posible si faltan.
    """
    _, paginas_recortadas = extraer_texto_limpio(ruta_pdf) # Importante tener la función de eliminar encabezados y pies de página

    texto_a_buscar = ""
    for page in paginas_recortadas[2:]:  # omitimos portada e índice
        texto = page.extract_text()
        if texto:
            texto_a_buscar += texto + "\n"

    # Si no se pasa nada, devolvemos todo el texto limpio
    if not any([titulo, inicio, fin]):
        return texto_a_buscar.strip()

    def patron_dinamico(texto, es_subtitulo=False):
        """
        Genera un patrón regex flexible con numeración opcional (4., 5.1., etc.)
        """
        if not texto:
            return None
        if es_subtitulo:
            return rf"\b\d+\.\d+\.\s*{re.escape(texto)}\b"
        else:
            return rf"\b\d+\.\s*{re.escape(texto)}\b"

    patron_titulo = patron_dinamico(titulo)
    patron_inicio = patron_dinamico(inicio, es_subtitulo=True)
    patron_fin = patron_dinamico(fin, es_subtitulo=True)

    # Paso 1: localizar el título principal si existe
    texto_post_titulo = texto_a_buscar
    if patron_titulo:
        match_titulo = re.search(patron_titulo, texto_a_buscar, flags=re.IGNORECASE)
        if match_titulo:
            texto_post_titulo = texto_a_buscar[match_titulo.end():]

    # Paso 2: buscar el inicio y fin dentro del texto posterior al título
    match_inicio = re.search(patron_inicio, texto_post_titulo, flags=re.IGNORECASE) if patron_inicio else None
    match_fin = re.search(patron_fin, texto_post_titulo, flags=re.IGNORECASE) if patron_fin else None

    # Casos posibles
    if match_inicio and match_fin:
        texto_extraido = texto_post_titulo[match_inicio.end():match_fin.start()]
    elif match_inicio and not match_fin:
        texto_extraido = texto_post_titulo[match_inicio.end():]
    elif not match_inicio and patron_titulo:
        texto_extraido = texto_post_titulo
    else:
        # Si no encuentra nada, devolvemos algo razonable
        texto_extraido = texto_a_buscar

    return texto_extraido.strip()

## Descripción de la asignatura
def extraer_descripcion_asignatura(ruta_pdf, model):
    descripcion_texto = extraer_seccion(
        ruta_pdf,
        titulo="Descripción de la asignatura y temario",
        inicio="Descripción de la asignatura",
        fin="Temario de la asignatura"
    )

    vector = model.encode(descripcion_texto).tolist()

    return descripcion_texto, vector

def extraer_competencias(entrada, model):
    texto_competencias = extraer_seccion(
        entrada,
        titulo="Competencias y resultados de aprendizaje",
        inicio="Competencias",
        fin="Resultados del aprendizaje"
    )
    codigos = re.findall(r'\n?([A-Z]{2}\d+)\s*-\s*', texto_competencias)
    textos = re.split(r'\n[A-Z]{2}\d+\s*-\s*', texto_competencias)
    textos = [t.replace('\n', ' ').strip() for t in textos if t.strip()]

    competencias = []
    for i, codigo in enumerate(codigos):
        texto_competencia = textos[i] if i < len(textos) else ""
        competencias.append({
            "codigo": codigo.strip(),
            "texto": texto_competencia,
        })
    if textos:
        vector = model.encode(" ".join(textos)).tolist()
    else:
        vector = []

    return competencias, vector

def extraer_conocimientos_previos(pdf_path, model):
    extraido = extraer_seccion(pdf_path, titulo="Conocimientos previos recomendados", inicio="Asignaturas previas que se recomienda haber cursado", fin="Competencias")
    conocimientos_previos = ""
    for line in extraido.splitlines():
        if not "Competencias y resultados de aprendizaje" in line:
            conocimientos_previos += line + "\n"
    conocimientos_previos = conocimientos_previos.strip()

    vector = model.encode(conocimientos_previos).tolist()

    return conocimientos_previos, vector

def extraer_temario_asignatura(ruta_pdf):
    """
    Extrae la sección 'Temario de la asignatura' de un PDF limpio usando páginas recortadas.
    Considera listas enumeradas jerárquicas y corta al detectar la siguiente sección.
    """
    _, paginas_recortadas = extraer_texto_limpio(ruta_pdf)

    texto_a_buscar = ""
    for page in paginas_recortadas[2:]:
        texto = page.extract_text()
        if texto:
            texto_a_buscar += texto + "\n"

    patron_temario = r"\b\d+\.\d+\.\s*Temario\s+de\s+la\s+asignatura\b"
    match_temario = re.search(patron_temario, texto_a_buscar, flags=re.IGNORECASE)
    if not match_temario:
        return "No se encontró el subtítulo 'Temario de la asignatura'."

    texto_post_temario = texto_a_buscar[match_temario.end():]
    lineas = texto_post_temario.splitlines()

    temario = []
    inicio_lista = False
    ultimo_numero_principal = None

    patron_lista = re.compile(r"^(\d+)(\.\d+)*\.\s+.+")  # patrón lista enumerada

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        match_item = patron_lista.match(linea)
        if match_item:
            numero_principal = int(match_item.group(1))  # primer número
            if ultimo_numero_principal is not None:
                # Detectamos salto en numeración -> fin del temario
                if numero_principal > ultimo_numero_principal + 1:
                    break
            ultimo_numero_principal = numero_principal
            inicio_lista = True
            temario.append(linea)
        else:
            if not inicio_lista:
                # Texto preliminar antes de la lista
                temario.append(linea)
            else:
                # Hemos empezado la lista y encontramos línea no numerada -> fin del temario
                break

    return "\n".join(temario).strip()

def estructurar_temario(temario_texto):
    """
    Convierte el temario plano en una estructura jerárquica basada en numeraciones (1., 1.1., 1.1.1., etc.)
    """
    lineas = temario_texto.splitlines()
    patron = re.compile(r"^(\d+(?:\.\d+)*)\.\s*(.+)")
    estructura = []
    temas_dict = {}

    for linea in lineas:
        linea = linea.strip()
        match = patron.match(linea)
        if not match:
            continue
        numero, titulo = match.groups()
        partes = numero.split(".")
        nivel = len(partes)

        # Creamos el nodo del tema
        nodo = {"numero": numero, "titulo": titulo, "subtemas": []}

        if nivel == 1:
            estructura.append(nodo)
            temas_dict[numero] = nodo
        else:
            padre_numero = ".".join(partes[:-1])
            padre = temas_dict.get(padre_numero)
            if padre:
                padre["subtemas"].append(nodo)
            temas_dict[numero] = nodo

    return estructura

def bulk_index_data(es, data, index_name):
    batch_size = 50  
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        actions = []
        for doc in batch:
            actions.append({
                "_index": index_name,
                "_id": doc['id_asignatura'],
                "_source": doc
            })
        resp = bulk(es, actions, raise_on_error=True)
        print("Indexed:", resp[0], "Errors:", resp[1])
    
def uri(base, tipo, id):
    return URIRef(f"{base}{tipo}/{id}")

def escape_rdf_literal(text):
    if text is None:
        return ""
    return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

def doc_to_triples(doc):
    subj = f"<http://upm.es/ontology/asignatura/{doc['id_asignatura']}>"
    triples = []

    triples.append(f'{subj} <http://upm.es/ontology/descripcion> "{escape_rdf_literal(doc.get("descripcion_asignatura",""))}" .')
    triples.append(f'{subj} <http://upm.es/ontology/conocimientosPrevios> "{escape_rdf_literal(doc.get("conocimientos_previos",""))}" .')

    for comp in doc.get("competencias", []):
        triples.append(f'{subj} <http://upm.es/ontology/competencia> "{escape_rdf_literal(comp.get("texto",""))}" .')
        triples.append(f'{subj} <http://upm.es/ontology/codigoCompetencia> "{escape_rdf_literal(comp.get("codigo",""))}" .')

    for tema in doc.get("temario", []):
        triples.append(f'{subj} <http://upm.es/ontology/tema> "{escape_rdf_literal(tema.get("titulo",""))}" .')
        for sub in tema.get("subtemas", []):
            triples.append(f'{subj} <http://upm.es/ontology/subtema> "{escape_rdf_literal(sub.get("titulo",""))}" .')

    return triples