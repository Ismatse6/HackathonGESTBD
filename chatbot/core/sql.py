from sqlalchemy import text

SQL_FIND_ASIG_BY_NAME = text(
    """
    SELECT id
    FROM asignaturas
    WHERE lower(unaccent(nombre)) LIKE lower(unaccent(:p))
    ORDER BY similarity(lower(nombre), lower(:raw)) DESC
    LIMIT 1
    """
)


SQL_GET_META = text(
    "SELECT id, nombre, numero_creditos, semestre, idioma FROM asignaturas WHERE id = :id"
)


SQL_GET_PROFES = text(
    """
    SELECT p.nombre AS profesor, p.correo_electronico AS correo
    FROM profesores p
    JOIN profesoresasignaturas pa ON pa.profesor_id = p.id
    WHERE pa.asignatura_id = :id
    ORDER BY p.nombre
    """
)


SQL_GET_BIBLIO = text(
    """
    SELECT b.titulo, b.autores, b.direccion_url
    FROM bibliografias b
    JOIN bibliografiaasignaturas ba ON ba.bibliografia_id = b.id
    WHERE ba.id_asignatura = :id
    ORDER BY b.titulo
    LIMIT 20
    """
)
