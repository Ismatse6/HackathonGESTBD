from typing import Optional

from pydantic import BaseModel


class MetaAsignatura(BaseModel):
    id: str
    nombre: str
    numero_creditos: Optional[str] = None
    agno_academico: Optional[str] = None
    semestre: Optional[str] = None
    idioma: Optional[str] = None


class BotAnswer(BaseModel):
    answer: str
    # asignatura_id: Optional[str] = None
    # citations: Optional[List[str]] = None
