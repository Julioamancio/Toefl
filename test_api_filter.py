import requests
import json

# Testar a API diretamente
url = "http://localhost:5000/api/students"
params = {"cefr_filter": "B2", "per_page": 10}

try:
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response text: {response.text[:500]}...")  # Primeiros 500 caracteres
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"Total de estudantes retornados: {len(data.get('students', []))}")
            print(f"Paginação total: {data.get('pagination', {}).get('total', 0)}")
            
            print("\nPrimeiros 5 estudantes:")
            for i, student in enumerate(data.get('students', [])[:5]):
                print(f"{i+1}. {student.get('name')} - Nível: {student.get('overall_level')}")
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e}")
    else:
        print(f"Erro na API: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Erro na requisição: {e}")