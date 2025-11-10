from typing import List, Literal

from elasticsearch import Elasticsearch

Sections = Literal[
    "descripcion_asignatura",
    "competencias.texto",
    "temario.titulo",
    "conocimientos_previos",
]


def es_field_search(
    es: Elasticsearch, index: str, asig_id: str, field: Sections
) -> List[str]:
    body = {
        "query": {
            "bool": {
                "filter": [{"term": {"id_asignatura": asig_id}}],
                "must": [{"exists": {"field": field}}],
            }
        },
        "_source": [field],
        "size": 3,
    }
    resp = es.search(index=index, body=body)
    chunks: List[str] = []
    for h in resp.get("hits", {}).get("hits", []):
        src = h.get("_source", {})
        val = src
        for k in field.split("."):
            val = val.get(k)
            if val is None:
                break
        if isinstance(val, str):
            chunks.append(val)
    return chunks
