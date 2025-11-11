from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import ES_URL, PG_DSN
from .models import MetaAsignatura
from .sql import (
    SQL_FIND_ASIG_BY_NAME,
    SQL_GET_BIBLIO,
    SQL_GET_ESCUELA,
    SQL_GET_META,
    SQL_GET_PROFES,
    SQL_GET_TITULACION,
)

_engine: Optional[Engine] = None
_es: Optional[Elasticsearch] = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(PG_DSN)
    return _engine


def get_es() -> Elasticsearch:
    global _es
    if _es is None:
        _es = Elasticsearch(ES_URL)
    return _es


def find_asignatura_id(nombre_o_id: str) -> Optional[str]:
    q = (nombre_o_id or "").strip()
    if q.isdigit() and 6 <= len(q) <= 9:
        return q
    with get_engine().begin() as conn:
        row = conn.execute(SQL_FIND_ASIG_BY_NAME, {"p": f"%{q}%", "raw": q}).first()
    return row[0] if row else None


def get_meta(asig_id: str) -> Optional[MetaAsignatura]:
    with get_engine().begin() as conn:
        row = conn.execute(SQL_GET_META, {"id": asig_id}).mappings().first()
    return MetaAsignatura(**row) if row else None


def get_profes(asig_id: str) -> List[Dict[str, str]]:
    with get_engine().begin() as conn:
        return [
            dict(r)
            for r in conn.execute(SQL_GET_PROFES, {"id": asig_id}).mappings().all()
        ]


def get_biblio(asig_id: str) -> List[Dict[str, Any]]:
    with get_engine().begin() as conn:
        return [
            dict(r)
            for r in conn.execute(SQL_GET_BIBLIO, {"id": asig_id}).mappings().all()
        ]


def get_titulacion(asig_id: str) -> List[Dict[str, Any]]:
    with get_engine().begin() as conn:
        return [
            dict(r)
            for r in conn.execute(SQL_GET_TITULACION, {"id": asig_id}).mappings().all()
        ]


def get_escuela(asig_id: str) -> List[Dict[str, Any]]:
    with get_engine().begin() as conn:
        return [
            dict(r)
            for r in conn.execute(SQL_GET_ESCUELA, {"id": asig_id}).mappings().all()
        ]
