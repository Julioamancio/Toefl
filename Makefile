# Makefile para TOEFL Dashboard
# Comandos disponíveis: make run, make seed, make test, make install, make clean

.PHONY: help install seed run test clean lint format check-deps

# Configurações
PYTHON = python
PIP = pip
FLASK_APP = app.py
FLASK_ENV = development
DB_FILE = toefl.db

# Comando padrão
help:
	@echo "TOEFL Dashboard - Comandos Disponíveis:"
	@echo ""
	@echo "  make install    - Instala todas as dependências"
	@echo "  make seed       - Inicializa o banco de dados e cria dados iniciais"
	@echo "  make run        - Inicia o servidor de desenvolvimento"
	@echo "  make test       - Executa os testes"
	@echo "  make lint       - Verifica qualidade do código"
	@echo "  make format     - Formata o código automaticamente"
	@echo "  make clean      - Remove arquivos temporários e cache"
	@echo "  make reset      - Remove banco e reinicializa (CUIDADO!)"
	@echo "  make check-deps - Verifica se as dependências estão instaladas"
	@echo ""
	@echo "Exemplos de uso:"
	@echo "  make install && make seed && make run"
	@echo ""

# Instalar dependências
install:
	@echo "Instalando dependências..."
	$(PIP) install -r requirements.txt
	@echo "Dependências instaladas com sucesso!"

# Verificar dependências
check-deps:
	@echo "Verificando dependências..."
	@$(PYTHON) -c "import flask, flask_sqlalchemy, flask_login, flask_wtf, pandas, openpyxl, xlrd, pytest; print('Todas as dependências estão instaladas!')"

# Inicializar banco de dados e criar dados iniciais
seed:
	@echo "Inicializando banco de dados..."
	$(PYTHON) init_db.py
	@echo "Banco de dados inicializado!"

# Executar aplicação
run:
	@echo "Iniciando servidor TOEFL Dashboard..."
	@echo "Acesse: http://localhost:5000"
	@echo "Pressione Ctrl+C para parar"
	@echo ""
	set FLASK_APP=$(FLASK_APP) && set FLASK_ENV=$(FLASK_ENV) && $(PYTHON) app.py

# Executar testes
test:
	@echo "Executando testes..."
	$(PYTHON) -m pytest tests/ -v --tb=short
	@echo "Testes concluídos!"

# Executar testes com cobertura
test-coverage:
	@echo "Executando testes com cobertura..."
	$(PYTHON) -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term
	@echo "Relatório de cobertura gerado em htmlcov/"

# Verificar qualidade do código
lint:
	@echo "Verificando qualidade do código..."
	@$(PYTHON) -c "import flake8" 2>/dev/null || echo "flake8 não instalado. Execute: pip install flake8"
	@$(PYTHON) -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || echo "Instale flake8 para verificação de código"

# Formatar código
format:
	@echo "Formatando código..."
	@$(PYTHON) -c "import black" 2>/dev/null || echo "black não instalado. Execute: pip install black"
	@$(PYTHON) -m black . --line-length=88 || echo "Instale black para formatação automática"

# Limpar arquivos temporários
clean:
	@echo "Limpando arquivos temporários..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist htmlcov rmdir /s /q htmlcov
	@if exist .coverage del .coverage
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@for /r . %%f in (*.pyc) do @if exist "%%f" del "%%f"
	@echo "Limpeza concluída!"

# Reset completo (CUIDADO!)
reset:
	@echo "ATENÇÃO: Isso irá remover o banco de dados atual!"
	@echo "Pressione Ctrl+C para cancelar ou Enter para continuar..."
	@pause
	@if exist $(DB_FILE) del $(DB_FILE)
	@echo "Banco removido. Execute 'make seed' para recriar."

# Backup do banco de dados
backup:
	@echo "Criando backup do banco de dados..."
	@if exist $(DB_FILE) (
		copy $(DB_FILE) $(DB_FILE).backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
		echo "Backup criado com sucesso!"
	) else (
		echo "Banco de dados não encontrado!"
	)

# Restaurar backup
restore:
	@echo "Restaurando backup mais recente..."
	@for /f "delims=" %%i in ('dir /b $(DB_FILE).backup.* 2^>nul ^| sort /r') do (
		copy "%%i" $(DB_FILE)
		echo "Backup %%i restaurado!"
		goto :done
	)
	@echo "Nenhum backup encontrado!"
	:done

# Informações do sistema
info:
	@echo "TOEFL Dashboard - Informações do Sistema"
	@echo "======================================="
	@echo "Python: "
	@$(PYTHON) --version
	@echo "Pip: "
	@$(PIP) --version
	@echo "Banco de dados: $(DB_FILE)"
	@if exist $(DB_FILE) (echo "Status: Existe") else (echo "Status: Não encontrado")
	@echo "Diretório atual: %CD%"
	@echo ""

# Desenvolvimento - servidor com reload automático
dev:
	@echo "Iniciando servidor de desenvolvimento com reload automático..."
	@echo "Acesse: http://localhost:5000"
	set FLASK_APP=$(FLASK_APP) && set FLASK_ENV=development && set FLASK_DEBUG=1 && $(PYTHON) -m flask run --host=0.0.0.0 --port=5000 --reload

# Produção - servidor básico
prod:
	@echo "Iniciando servidor em modo produção..."
	set FLASK_ENV=production && $(PYTHON) app.py

# Instalar dependências de desenvolvimento
install-dev:
	@echo "Instalando dependências de desenvolvimento..."
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov flake8 black
	@echo "Dependências de desenvolvimento instaladas!"

# Gerar requirements.txt atualizado
freeze:
	@echo "Gerando requirements.txt atualizado..."
	$(PIP) freeze > requirements.txt
	@echo "requirements.txt atualizado!"

# Verificar se o servidor está rodando
status:
	@echo "Verificando status do servidor..."
	@$(PYTHON) -c "import requests; r=requests.get('http://localhost:5000'); print('Servidor rodando!' if r.status_code==200 else 'Servidor não está rodando')" 2>/dev/null || echo "Servidor não está rodando ou requests não instalado"