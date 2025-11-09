CREATE TABLE Titulaciones (
    id VARCHAR(10) PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    tipo_estudio VARCHAR(100) NOT NULL
);

CREATE TABLE Escuelas (
    id INT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    entidad_dbpedia VARCHAR(255) NOT NULL
);

CREATE TABLE Profesores (
    id INT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo_electronico VARCHAR(100) NOT NULL
);

CREATE TABLE Asignaturas (
    id INT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    numero_creditos INT NOT NULL,
    agno_academico VARCHAR(100) NOT NULL,
    semestre VARCHAR(100) NOT NULL,
    idioma VARCHAR(100) NOT NULL
);

CREATE TABLE Bibliografias (
    id INT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    autores VARCHAR(150) NOT NULL,
    direccion_url VARCHAR(255) NOT NULL
);

CREATE TABLE ProfesoresAsignaturas (
    profesor_id INT NOT NULL,
    asignatura_id INT NOT NULL,
    FOREIGN KEY (profesor_id) REFERENCES Profesores(id),
    FOREIGN KEY (asignatura_id) REFERENCES Asignaturas(id),
    PRIMARY KEY (profesor_id, asignatura_id)
);

CREATE TABLE TitulacionesEscuelas (
    titulacion_id VARCHAR(10) NOT NULL,
    escuela_id INT NOT NULL,
    FOREIGN KEY (titulacion_id) REFERENCES Titulaciones(id),
    FOREIGN KEY (escuela_id) REFERENCES Escuelas(id),
    PRIMARY KEY (titulacion_id, escuela_id)
);

CREATE TABLE TitulacionesAsignaturas (
    titulacion_id VARCHAR(10) NOT NULL,
    asignatura_id INT NOT NULL,
    FOREIGN KEY (titulacion_id) REFERENCES Titulaciones(id),
    FOREIGN KEY (asignatura_id) REFERENCES Asignaturas(id),
    PRIMARY KEY (titulacion_id, asignatura_id)
);

CREATE TABLE BibliografiaAsignaturas (
    asignatura_id INT NOT NULL,
    bibliografia_id INT NOT NULL,
    FOREIGN KEY (asignatura_id) REFERENCES Asignaturas(id),
    FOREIGN KEY (bibliografia_id) REFERENCES Bibliografias(id),
    PRIMARY KEY (asignatura_id, bibliografia_id)
);