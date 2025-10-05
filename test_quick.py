#!/usr/bin/env python3
"""
Teste rápido para verificar se o editor de certificados está funcionando
"""
import requests
import json
import sys

def test_certificate_editor():
    print("🔍 Testando editor de certificados...")
    
    try:
        # Testar se o servidor está rodando
        print("1. Verificando se servidor está ativo...")
        response = requests.get('http://localhost:5000', timeout=5)
        print(f"   ✅ Servidor ativo (status: {response.status_code})")
        
        # Testar página de login
        print("2. Testando página de login...")
        login_page = requests.get('http://localhost:5000/login', timeout=5)
        print(f"   ✅ Página de login acessível (status: {login_page.status_code})")
        
        # Fazer login
        print("3. Fazendo login como admin...")
        session = requests.Session()
        
        # Primeiro obter a página de login para pegar o CSRF token
        login_page = session.get('http://localhost:5000/login', timeout=5)
        
        # Extrair CSRF token
        csrf_token = None
        import re
        match = re.search(r'csrf-token.*?content="([^"]+)"', login_page.text)
        if match:
            csrf_token = match.group(1)
            print(f"   🔑 CSRF token obtido: {csrf_token[:20]}...")
        else:
            print("   ⚠️  CSRF token não encontrado na página de login")
        
        # Fazer login com CSRF token
        login_data = {
            'username': 'admin', 
            'password': 'admin',
            'csrf_token': csrf_token
        }
        login_response = session.post('http://localhost:5000/login', data=login_data, timeout=10)
        
        if login_response.status_code == 200 and 'alunos' in login_response.url:
            print("   ✅ Login realizado com sucesso")
        else:
            print(f"   ❌ Falha no login (status: {login_response.status_code})")
            return False
        
        # Testar página de alunos
        print("4. Acessando página de alunos...")
        students_page = session.get('http://localhost:5000/alunos', timeout=5)
        print(f"   ✅ Página de alunos acessível (status: {students_page.status_code})")
        
        # Testar editor de certificados
        print("5. Acessando editor de certificados...")
        editor_page = session.get('http://localhost:5000/certificate/editor/1', timeout=5)
        
        if editor_page.status_code == 200:
            print("   ✅ Editor de certificados acessível")
            
            # Verificar se há elementos essenciais na página
            if 'savePositions' in editor_page.text:
                print("   ✅ Função savePositions encontrada no JavaScript")
            else:
                print("   ⚠️  Função savePositions não encontrada")
                
            if 'csrf-token' in editor_page.text:
                print("   ✅ Token CSRF encontrado na página")
            else:
                print("   ⚠️  Token CSRF não encontrado")
                
        else:
            print(f"   ❌ Editor não acessível (status: {editor_page.status_code})")
            return False
            
        print("\n🎉 TESTE CONCLUÍDO - Editor de certificados está funcionando!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Não foi possível conectar ao servidor Flask")
        print("   Verifique se o servidor está rodando em http://localhost:5000")
        return False
    except requests.exceptions.Timeout:
        print("❌ ERRO: Timeout na conexão com o servidor")
        return False
    except Exception as e:
        print(f"❌ ERRO INESPERADO: {e}")
        return False

if __name__ == "__main__":
    success = test_certificate_editor()
    sys.exit(0 if success else 1)