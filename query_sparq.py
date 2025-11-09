import requests

GRAPHDB_ENDPOINT = "http://localhost:8000/repositories/prueba2"

query = """
PREFIX upm: <http://upm.es/ontology/>
SELECT ?s ?o
WHERE {
	?s upm:nombre ?o .
} LIMIT 100
"""

response = requests.post(
    GRAPHDB_ENDPOINT,
    data={'query': query},
    headers={'Accept': 'application/sparql-results+json'}
)

if response.status_code == 200:
    results = response.json()
    print(results)
    for r in results['results']['bindings']:
        print(r)
else:
    print("Error:", response.status_code, response.text)