#!/usr/bin/env python3
"""
Script para testar o salvamento de posições no editor de certificados
"""

import requests
import json
import re
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def get_csrf_token(session):
    """Obtém o token CSRF da página de login"""
    try:
        response = session.get(f"{BASE_URL}/login")
        if response.status_code == 200:
            # Procurar pelo token CSRF no HTML
            csrf_match = re.search(r'name="csrf_token"\s+[^>]*value="([^"]+)"', response.text)
            if csrf_match:
                return csrf_match.group(1)
            # Fallback: meta csrf-token presente no base.html
            meta_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
            if meta_match:
                return meta_match.group(1)
        return None
    except Exception as e:
        print(f"❌ Erro ao obter token CSRF: {e}")
        return None

def login_as_admin(session):
    """Faz login como admin"""
    try:
        # Obter token CSRF
        csrf_token = get_csrf_token(session)
        if not csrf_token:
            print("❌ Não foi possível obter token CSRF")
            return False
        
        # Dados de login
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrf_token': csrf_token
        }
        
        # Fazer login
        response = session.post(f"{BASE_URL}/login", data=login_data)
        
        # Considerar redirects para '/alunos' ou '/dash' como sucesso
        final_url = response.url
        if response.status_code == 200 and ('alunos' in final_url or 'dash' in final_url):
            print("✅ Login como admin realizado com sucesso")
            return True
        else:
            print(f"❌ Falha no login: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return False

def test_save_positions(session):
    """Testa o salvamento de posições"""
    try:
        print("🧪 Testando salvamento de posições...")
        
        # Obter token CSRF para requisições JSON
        csrf_token = get_csrf_token(session)
        
        # Dados de teste para salvamento
        test_data = {
            'student_id': 1,  # Assumindo que existe um estudante com ID 1
            'positions': json.dumps({
                'name': {'x': 100, 'y': 200},
                'score': {'x': 150, 'y': 250},
                'date': {'x': 200, 'y': 300}
            }),
            'colors': json.dumps({
                'name': '#000000',
                'score': '#333333',
                'date': '#666666'
            }),
            'certificate_date': '2024-01-15'
        }
        
        # Fazer requisição para salvar posições
        headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
        response = session.post(f"{BASE_URL}/api/certificate/save-positions", json=test_data, headers=headers)
        
        print(f"📊 Status da resposta: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Salvamento bem-sucedido: {result}")
            return True
        else:
            print(f"❌ Falha no salvamento: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📋 Detalhes do erro: {error_data}")
            except:
                print(f"📋 Resposta de erro: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de salvamento: {e}")
        return False

def test_load_positions(session):
    """Testa o carregamento de posições"""
    try:
        print("🧪 Testando carregamento de posições...")
        
        # Fazer requisição para carregar posições
        response = session.get(f"{BASE_URL}/api/certificate/load-positions", params={'student_id': 1})
        
        print(f"📊 Status da resposta: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Carregamento bem-sucedido: {result}")
            return True
        else:
            print(f"❌ Falha no carregamento: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📋 Detalhes do erro: {error_data}")
            except:
                print(f"📋 Resposta de erro: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de carregamento: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Iniciando teste de salvamento de posições...")
    print(f"🌐 URL base: {BASE_URL}")
    
    # Criar sessão
    session = requests.Session()
    
    # Verificar se servidor está rodando
    try:
        response = session.get(BASE_URL)
        if response.status_code != 200:
            print(f"❌ Servidor não está respondendo: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Não foi possível conectar ao servidor: {e}")
        return False
    
    print("✅ Servidor está rodando")
    
    # Fazer login
    if not login_as_admin(session):
        return False
    
    # Testar salvamento
    save_success = test_save_positions(session)
    
    # Testar carregamento
    load_success = test_load_positions(session)
    
    if save_success and load_success:
        print("🎉 Todos os testes passaram! O editor de certificados está funcionando.")
        return True
    else:
        print("💥 Alguns testes falharam.")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)