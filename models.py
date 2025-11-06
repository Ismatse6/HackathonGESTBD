from typing import List
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.associationproxy import association_proxy


class Base(DeclarativeBase):
    pass


class Titulacion(Base):
    __tablename__ = "Titulaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo_estudio: Mapped[str] = mapped_column(String(100), nullable=False)
    plan_estudios: Mapped[str] = mapped_column(String(100), nullable=False)

    # relaciones
    asignaturas: Mapped[List["Asignatura"]] = relationship(
        "Asignatura", back_populates="titulacion_obj", cascade="all, delete-orphan"
    )
    escuelas_assoc: Mapped[List["TitulacionesEscuelas"]] = relationship(
        "TitulacionesEscuelas", back_populates="titulacion", cascade="all, delete-orphan"
    )
    escuelas: Mapped[List["Escuela"]] = association_proxy("escuelas_assoc", "escuela")

    def __repr__(self):
        return f"<Titulacion(id={self.id}, nombre={self.nombre!r})>"


class Escuela(Base):
    __tablename__ = "Escuelas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    direccion_url: Mapped[str] = mapped_column(String(255), nullable=False)

    titulaciones_assoc: Mapped[List["TitulacionesEscuelas"]] = relationship(
        "TitulacionesEscuelas", back_populates="escuela", cascade="all, delete-orphan"
    )
    titulaciones: Mapped[List[Titulacion]] = association_proxy("titulaciones_assoc", "titulacion")

    def __repr__(self):
        return f"<Escuela(id={self.id}, nombre={self.nombre!r})>"


class TitulacionesEscuelas(Base):
    """
    Tabla de asociación N:M entre Titulaciones y Escuelas.
    Tiene su propia PK (como en tu DDL).
    """
    __tablename__ = "TitulacionesEscuelas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulacion_id: Mapped[int] = mapped_column(Integer, ForeignKey("Titulaciones.id"), nullable=False)
    escuela_id: Mapped[int] = mapped_column(Integer, ForeignKey("Escuelas.id"), nullable=False)

    titulacion: Mapped[Titulacion] = relationship("Titulacion", back_populates="escuelas_assoc")
    escuela: Mapped[Escuela] = relationship("Escuela", back_populates="titulaciones_assoc")

    def __repr__(self):
        return f"<TitulacionesEscuelas(id={self.id}, titulacion_id={self.titulacion_id}, escuela_id={self.escuela_id})>"


class Profesor(Base):
    __tablename__ = "Profesores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    correo_electronico: Mapped[str] = mapped_column(String(100), nullable=False)
    categoria_academica: Mapped[str] = mapped_column(String(100), nullable=False)

    # relación con la tabla de asociación ProfesoresAsignaturas
    asignaturas_assoc: Mapped[List["ProfesoresAsignaturas"]] = relationship(
        "ProfesoresAsignaturas", back_populates="profesor", cascade="all, delete-orphan"
    )
    # proxy para obtener list[Asignatura] directamente
    asignaturas: Mapped[List["Asignatura"]] = association_proxy("asignaturas_assoc", "asignatura")

    def __repr__(self):
        return f"<Profesor(id={self.id}, nombre={self.nombre!r})>"


class Asignatura(Base):
    __tablename__ = "Asignaturas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    coordinador: Mapped[str] = mapped_column(String(100), nullable=False)
    numero_creditos: Mapped[int] = mapped_column(Integer, nullable=False)
    agno_academico: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion_url: Mapped[str] = mapped_column(String(255), nullable=False)
    semestre: Mapped[str] = mapped_column(String(100), nullable=False)
    idioma: Mapped[str] = mapped_column(String(100), nullable=False)
    id_guia_docente: Mapped[int] = mapped_column(Integer, nullable=False)

    titulacion: Mapped[int] = mapped_column(Integer, ForeignKey("Titulaciones.id"), nullable=False)
    titulacion_obj: Mapped[Titulacion] = relationship("Titulacion", back_populates="asignaturas")

    profesores_assoc: Mapped[List["ProfesoresAsignaturas"]] = relationship(
        "ProfesoresAsignaturas", back_populates="asignatura", cascade="all, delete-orphan"
    )
    profesores: Mapped[List[Profesor]] = association_proxy("profesores_assoc", "profesor")

    def __repr__(self):
        return f"<Asignatura(id={self.id}, nombre={self.nombre!r})>"


class ProfesoresAsignaturas(Base):
    """
    Tabla de asociación N:M entre Profesores y Asignaturas.
    """
    __tablename__ = "ProfesoresAsignaturas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profesor_id: Mapped[int] = mapped_column(Integer, ForeignKey("Profesores.id"), nullable=False)
    asignatura_id: Mapped[int] = mapped_column(Integer, ForeignKey("Asignaturas.id"), nullable=False)

    profesor: Mapped[Profesor] = relationship("Profesor", back_populates="asignaturas_assoc")
    asignatura: Mapped[Asignatura] = relationship("Asignatura", back_populates="profesores_assoc")

    def __repr__(self):
        return f"<ProfesoresAsignaturas(id={self.id}, profesor_id={self.profesor_id}, asignatura_id={self.asignatura_id})>"
