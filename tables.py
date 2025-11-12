from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def create_tables(engine):
    Base.metadata.create_all(engine)
    
class Titulacion(Base):
    __tablename__ = "titulaciones"
    id = Column(String(10), primary_key=True)
    nombre = Column(String(150), nullable=False)
    tipo_estudio = Column(String(100), nullable=False)

    escuelas = relationship("escuela", secondary="titulacionesescuelas", back_populates="titulaciones")
    asignaturas = relationship("asignatura", secondary="titulacionesasignaturas", back_populates="titulaciones")


class Escuela(Base):
    __tablename__ = "escuelas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    entidad_dbpedia = Column(String(255), nullable=False)

    titulaciones = relationship("titulacion", secondary="titulacionesescuelas", back_populates="escuelas")
    profesores = relationship("profesor", back_populates="escuela")


class Profesor(Base):
    __tablename__ = "profesores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    correo_electronico = Column(String(100), nullable=False)

    escuela_id = Column(Integer, ForeignKey("escuelas.id"))
    escuela = relationship("escuela", back_populates="profesores")
    asignaturas = relationship("asignatura", secondary="profesoresasignaturas", back_populates="profesores")


class Asignatura(Base):
    __tablename__ = "asignaturas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    numero_creditos = Column(Integer, nullable=False)
    agno_academico = Column(String(100), nullable=False)
    semestre = Column(String(100), nullable=False)
    idioma = Column(String(100), nullable=False)
    titulacion_id = Column(String(10), ForeignKey("titulaciones.id"))

    titulaciones = relationship("titulacion", secondary="titulacionesasignaturas", back_populates="asignaturas")
    profesores = relationship("profesor", secondary="profesoresasignaturas", back_populates="asignaturas")
    bibliografias = relationship("bibliografia", secondary="bibliografiaasignaturas", back_populates="asignaturas")


class Bibliografia(Base):
    __tablename__ = "bibliografias"
    id = Column(Integer, primary_key=True)
    titulo = Column(String(255), nullable=False)
    autores = Column(String(150), nullable=False)
    direccion_url = Column(String(255), nullable=False)

    asignaturas = relationship("asignatura", secondary="bibliografiaasignaturas", back_populates="bibliografias")


class ProfesoresAsignaturas(Base):
    __tablename__ = "profesoresasignaturas"
    profesor_id = Column(Integer, ForeignKey("profesores.id"), primary_key=True)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), primary_key=True)


class TitulacionesEscuelas(Base):
    __tablename__ = "titulacionesescuelas"
    titulacion_id = Column(String(10), ForeignKey("titulaciones.id"), primary_key=True)
    escuela_id = Column(Integer, ForeignKey("escuelas.id"), primary_key=True)


class TitulacionesAsignaturas(Base):
    __tablename__ = "titulacionesasignaturas"
    titulacion_id = Column(String(10), ForeignKey("titulaciones.id"), primary_key=True)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), primary_key=True)


class BibliografiasAsignaturas(Base):
    __tablename__ = "bibliografiaasignaturas"
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), primary_key=True)
    bibliografia_id = Column(Integer, ForeignKey("bibliografias.id"), primary_key=True)
