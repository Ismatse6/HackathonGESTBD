from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def create_tables(engine):
    Base.metadata.create_all(engine)
    
class Titulacion(Base):
    __tablename__ = "Titulaciones"
    id = Column(String(10), primary_key=True)
    nombre = Column(String(150), nullable=False)
    tipo_estudio = Column(String(100), nullable=False)

    escuelas = relationship("Escuela", secondary="TitulacionesEscuelas", back_populates="titulaciones")
    asignaturas = relationship("Asignatura", secondary="TitulacionesAsignaturas", back_populates="titulaciones")


class Escuela(Base):
    __tablename__ = "Escuelas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    entidad_dbpedia = Column(String(255), nullable=False)

    titulaciones = relationship("Titulacion", secondary="TitulacionesEscuelas", back_populates="escuelas")
    profesores = relationship("Profesor", back_populates="escuela")


class Profesor(Base):
    __tablename__ = "Profesores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    correo_electronico = Column(String(100), nullable=False)

    escuela_id = Column(Integer, ForeignKey("Escuelas.id"))
    escuela = relationship("Escuela", back_populates="profesores")
    asignaturas = relationship("Asignatura", secondary="ProfesoresAsignaturas", back_populates="profesores")


class Asignatura(Base):
    __tablename__ = "Asignaturas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    numero_creditos = Column(Integer, nullable=False)
    agno_academico = Column(String(100), nullable=False)
    semestre = Column(String(100), nullable=False)
    idioma = Column(String(100), nullable=False)

    titulaciones = relationship("Titulacion", secondary="TitulacionesAsignaturas", back_populates="asignaturas")
    profesores = relationship("Profesor", secondary="ProfesoresAsignaturas", back_populates="asignaturas")
    bibliografias = relationship("Bibliografia", secondary="BibliografiaAsignaturas", back_populates="asignaturas")


class Bibliografia(Base):
    __tablename__ = "Bibliografias"
    id = Column(Integer, primary_key=True)
    titulo = Column(String(255), nullable=False)
    autores = Column(String(150), nullable=False)
    direccion_url = Column(String(255), nullable=False)

    asignaturas = relationship("Asignatura", secondary="BibliografiaAsignaturas", back_populates="bibliografias")


class ProfesoresAsignaturas(Base):
    __tablename__ = "ProfesoresAsignaturas"
    profesor_id = Column(Integer, ForeignKey("Profesores.id"), primary_key=True)
    asignatura_id = Column(Integer, ForeignKey("Asignaturas.id"), primary_key=True)


class TitulacionesEscuelas(Base):
    __tablename__ = "TitulacionesEscuelas"
    titulacion_id = Column(String(10), ForeignKey("Titulaciones.id"), primary_key=True)
    escuela_id = Column(Integer, ForeignKey("Escuelas.id"), primary_key=True)


class TitulacionesAsignaturas(Base):
    __tablename__ = "TitulacionesAsignaturas"
    titulacion_id = Column(String(10), ForeignKey("Titulaciones.id"), primary_key=True)
    asignatura_id = Column(Integer, ForeignKey("Asignaturas.id"), primary_key=True)


class BibliografiasAsignaturas(Base):
    __tablename__ = "BibliografiaAsignaturas"
    asignatura_id = Column(Integer, ForeignKey("Asignaturas.id"), primary_key=True)
    bibliografia_id = Column(Integer, ForeignKey("Bibliografias.id"), primary_key=True)