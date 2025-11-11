from typing import List, Literal, Set

from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

Sections = Literal[
    "descripcion_vector",
    "competencias_vector",
    "conocimientos_previos_vector",
]


def es_temario_search(es: Elasticsearch, index: str, id_asignatura: str) -> List[str]:
    query = {
        "query": {"term": {"id_asignatura": id_asignatura}},
        "_source": ["temario"],
    }

    res = es.search(index=index, body=query)
    temario_list = []

    for hit in res.get("hits", {}).get("hits", []):
        temario = hit.get("_source", {}).get("temario", [])
        for tema in temario:
            temario_list.append(
                f"Tema {tema.get('numero', '')}: {tema.get('titulo', '')}"
            )

            for subtema in tema.get("subtemas", []):
                temario_list.append(
                    f"\tSubtema {subtema.get('numero', '')}: {subtema.get('titulo', '')}"
                )

    return temario_list


def es_competencias_search(
    es: Elasticsearch, index: str, id_asignatura: str
) -> List[str]:
    query = {
        "query": {"term": {"id_asignatura": id_asignatura}},
        "_source": ["competencias"],
    }

    res = es.search(index=index, body=query)
    competencias_list = []

    for hit in res.get("hits", {}).get("hits", []):
        competencias = hit.get("_source", {}).get("competencias", [])
        for comp in competencias:
            codigo = comp.get("codigo", "")
            texto = comp.get("texto", "")
            if codigo:
                competencias_list.append(f"Competencia {codigo}: {texto}")
            else:
                competencias_list.append(f"Competencia: {texto}")

    return competencias_list


def es_descripcion_search(
    es: Elasticsearch, index: str, id_asignatura: str
) -> List[str]:
    query = {
        "query": {"term": {"id_asignatura": id_asignatura}},
        "_source": ["descripcion_asignatura"],
    }

    res = es.search(index=index, body=query)
    descripcion_list = []

    for hit in res.get("hits", {}).get("hits", []):
        descripcion = hit.get("_source", {}).get("descripcion_asignatura", "")
        if descripcion:
            descripcion_list.append(descripcion)

    return descripcion_list


def es_conocimientos_previos_search(
    es: Elasticsearch, index: str, id_asignatura: str
) -> List[str]:
    query = {
        "query": {"term": {"id_asignatura": id_asignatura}},
        "_source": ["conocimientos_previos"],
    }

    res = es.search(index=index, body=query)
    conocimientos_list = []

    for hit in res.get("hits", {}).get("hits", []):
        conocimientos = hit.get("_source", {}).get("conocimientos_previos", "")
        if conocimientos:
            conocimientos_list.append(conocimientos)

    return conocimientos_list


def es_field_search(
    es: Elasticsearch,
    index: str,
    query_text: str,
    field: Sections,
    *,
    hits_size: int = 10,
    max_subjects: int = 3,
) -> List[str]:
    model = SentenceTransformer("distiluse-base-multilingual-cased-v2")
    query_vector = model.encode(query_text).tolist()

    match field:
        case "descripcion_vector":
            source = ["id_asignatura", "nombre_asignatura", "descripcion_asignatura"]
        case "conocimientos_previos_vector":
            source = ["id_asignatura", "nombre_asignatura", "conocimientos_previos"]
        case "competencias_vector":
            source = ["id_asignatura", "nombre_asignatura", "competencias"]

    res = es.search(
        index=index,
        size=hits_size,
        knn={
            "field": field,
            "query_vector": query_vector,
            "k": hits_size,
            "num_candidates": max(hits_size * 5, 100),
        },
        _source=source,
    )

    chunks: List[str] = []
    seen_subjects: Set[str] = set()

    for hit in res.get("hits", {}).get("hits", []):
        src = hit.get("_source", {}) or {}
        nombre = src.get("nombre_asignatura") or "Asignatura"
        asig_id = str(src.get("id_asignatura") or "?")
        prefix = f"{asig_id} - {nombre}: "

        if len(seen_subjects) >= max_subjects:
            break
        if nombre in seen_subjects:
            continue

        if field == "competencias_vector":
            comps = src.get("competencias", []) or []
            if not comps:
                continue
            seen_subjects.add(nombre)
            for comp in comps:
                codigo = (comp or {}).get("codigo") or ""
                texto = (comp or {}).get("texto") or ""
                if not texto:
                    continue
                if codigo:
                    chunks.append(f"{prefix}Competencia {codigo}: {texto}")
                else:
                    chunks.append(f"{prefix}Competencia: {texto}")
            continue

        collected_any = False
        tmp_chunks: List[str] = []
        for key in source:
            if key in ("nombre_asignatura", "id_asignatura"):
                continue
            val = src
            for subk in key.split("."):
                if not isinstance(val, dict):
                    val = None
                    break
                val = val.get(subk)
                if val is None:
                    break
            if isinstance(val, str) and val.strip():
                tmp_chunks.append(prefix + val.strip())
                collected_any = True

        if collected_any:
            seen_subjects.add(nombre)
            chunks.extend(tmp_chunks)

    return chunks
