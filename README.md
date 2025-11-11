# Gestión de Sistemas de Datos Masivos

Este repositorio implementa un sistema para la **extracción**, **procesamiento** y **explotación de datos** a partir de las **guías docentes de las asignaturas** de la *Universidad Politécnica de Madrid*.  

El sistema se apoya en tres tipos de almacenamiento, cada uno con un propósito específico:  

- **Base de datos relacional (PostgreSQL):** almacena los metadatos del sistema.  
- **Base de datos no relacional (Elasticsearch):** almacena el contenido procesado de las guías docentes.  
- **Grafo de conocimiento (GraphDB):** almacena las tripletas de la ontología utilizada para enlazar y relacionar todos los datos.  

El proyecto está completamente desarrollado en **Python**. Los principales archivos de ejecución son:  

- **`Pipeline.py`**: se encarga de descargar los datos, procesar las guías docentes y materializar la información en el sistema.  
- **`Utils.py`**: contiene funciones auxiliares utilizadas por `Pipeline.py`.  
- **`Consultas.ipynb`**: cuaderno de Jupyter para realizar consultas sobre el sistema de datos.
- **`Chatbot`**: directorio que contiene el codigo para la ejecución de un chatbot que se alimente de los datos de nuestro sistema.

---

## Autores

- Daniel Acosta Luna  
- Iván Álvarez García  
- Cristina Marzo Pardos  
- Ismael Tse Perdomo Rodríguez
