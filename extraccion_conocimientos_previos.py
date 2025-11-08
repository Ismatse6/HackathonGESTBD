import re
import pdfplumber
import sys

# Los márgenes de 60 ptos en principio son suficiente para todas las guías
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

def main():
    if len(sys.argv) < 2:
        print("Uso: python extraccion_conocimientos_previos.py <ruta_fichero_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    #pdf_path = "./GA_61AH_613000129_1S_2025-26.pdf"
    #pdf_path = "./GA_61AH_613000133_2S_2025-26.pdf"
    extraido = extraer_seccion(pdf_path, titulo="Conocimientos previos recomendados", inicio="Asignaturas previas que se recomienda haber cursado", fin="Competencias")
    limpio = ""
    for line in extraido.splitlines():
        if not "Competencias y resultados de aprendizaje" in line:
            limpio += line + "\n"
    limpio = limpio.strip()
    print(limpio)

if __name__ == "__main__":
    main()