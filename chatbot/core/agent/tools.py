from typing import List, Optional

from pydantic_ai import Agent

from ..config import ES_INDEX
from ..data_access import (
    find_asignatura_id,
    get_biblio,
    get_es,
    get_escuela,
    get_meta,
    get_profes,
    get_titulacion,
)
from ..es_search import Sections, es_field_search
from ..models import MetaAsignatura


def register_tools(agent: Agent) -> None:
    @agent.tool_plain
    def resolve_asignatura_id(q: str) -> Optional[str]:
        """Dada una cadena con un posible ID o nombre, devuelve un ID de asignatura válido o null."""
        return find_asignatura_id(q)

    @agent.tool_plain
    def fetch_meta(asignatura_id: str) -> Optional[MetaAsignatura]:
        """Metadatos básicos de la asignatura (ECTS, idioma, semestre)."""
        return get_meta(asignatura_id)

    @agent.tool_plain
    def fetch_profes(asignatura_id: str):
        """Lista de profesores y correos."""
        return get_profes(asignatura_id)

    @agent.tool_plain
    def fetch_biblio(asignatura_id: str):
        """Bibliografía enlazada a la asignatura."""
        return get_biblio(asignatura_id)

    @agent.tool_plain
    def fetch_titulacion(asignatura_id: str):
        """Titulación enlazada a la asignatura."""
        return get_titulacion(asignatura_id)

    @agent.tool_plain
    def fetch_escuela(asignatura_id: str):
        """Escuela enlazada a la titulación enlazada a la asignatura."""
        return get_escuela(asignatura_id)

    @agent.tool_plain
    def fetch_es_section(asignatura_id: str, section: Sections) -> List[str]:
        """Devuelve hasta 3 fragmentos textuales de ES para la sección pedida."""
        return es_field_search(get_es(), ES_INDEX, asignatura_id, section)
