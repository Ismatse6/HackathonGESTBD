CREATE TABLE Titulaciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    tipo_estudio VARCHAR(100) NOT NULL,
    plan_estudios VARCHAR(100) NOT NULL
);

CREATE TABLE Escuelas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    direccion VARCHAR(255) NOT NULL,
    direccion_url VARCHAR(255) NOT NULL
);

CREATE TABLE Profesores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo_electronico VARCHAR(100) NOT NULL,
    categoria_academica VARCHAR(100) NOT NULL
);

CREATE TABLE Asignaturas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    coordinador VARCHAR(100) NOT NULL,
    numero_creditos INT NOT NULL,
    agno_academico VARCHAR(100) NOT NULL,
    direccion_url VARCHAR(255) NOT NULL,
    semestre VARCHAR(100) NOT NULL,
    idioma VARCHAR(100) NOT NULL,
    id_guia_docente INT NOT NULL,
    titulacion INT NOT NULL,
    FOREIGN KEY (titulacion) REFERENCES Titulaciones(id)
);

CREATE TABLE ProfesoresAsignaturas (
    id SERIAL PRIMARY KEY,
    profesor_id INT NOT NULL,
    asignatura_id INT NOT NULL,
    FOREIGN KEY (profesor_id) REFERENCES Profesores(id),
    FOREIGN KEY (asignatura_id) REFERENCES Asignaturas(id)
);

CREATE TABLE TitulacionesEscuelas (
    id SERIAL PRIMARY KEY,
    titulacion_id INT NOT NULL,
    escuela_id INT NOT NULL,
    FOREIGN KEY (titulacion_id) REFERENCES Titulaciones(id),
    FOREIGN KEY (escuela_id) REFERENCES Escuelas(id)
);

CREATE TABLE Bibliografias (
    id SERIAL PRIMARY KEY,
    asignatura_id INT, 
    nombre VARCHAR(100),
    autores VARCHAR(100),
    url VARCHAR(200),
    FOREIGN KEY (asignatura_id) REFERENCES Asignaturas(id)  
);
