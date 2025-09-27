# TOEFL Junior Dashboard

Dashboard interativo e moderno para análise de resultados do TOEFL Junior com mapeamento automático para níveis CEFR (A1-C2).

## 🚀 Funcionalidades

### 📊 Dashboard Principal
- **Estatísticas gerais**: Total de alunos, turmas, média geral e nível CEFR predominante
- **Gráficos interativos**: Distribuição por níveis CEFR e médias por habilidade
- **Rankings**: Top 10 melhores alunos e alunos que precisam de atenção
- **Visualização responsiva** com Chart.js

### 📤 Sistema de Upload
- **Importação de arquivos**: Excel (.xlsx, .xls) e CSV
- **Validação automática**: Verificação de colunas obrigatórias e tipos de dados
- **Preview dos dados**: Visualização antes da importação
- **Tratamento de duplicatas**: Atualização automática baseada no StudentNumber
- **Histórico de uploads**: Controle de todas as importações realizadas

### 👥 Gerenciamento de Alunos
- **Listagem completa**: Tabela paginada e ordenável
- **Filtros avançados**: Por turma, nível CEFR e busca por nome
- **Perfil individual**: Detalhes completos com gráficos de desempenho
- **Exportação**: Download dos dados em CSV
- **Comparação de turmas**: Análise comparativa de desempenho

### 🏫 Sistema de Turmas
- **Criação e edição**: Gerenciamento completo de turmas
- **Estatísticas por turma**: Métricas específicas de cada classe
- **Vinculação de alunos**: Associação automática durante a importação
- **Status ativo/inativo**: Controle de turmas ativas

### 🔐 Autenticação e Segurança
- **Login obrigatório**: Acesso protegido a todas as funcionalidades
- **Níveis de usuário**: Administrador e usuário comum
- **Gerenciamento de usuários**: Criação, edição e desativação (apenas admin)
- **Sessões seguras**: Controle de acesso com Flask-Login
- **Validação de arquivos**: Verificação de tipo MIME e tamanho

## 📋 Colunas Obrigatórias do Excel/CSV

| Coluna | Descrição | Exemplo |
|--------|-----------|----------|
| `Name` | Nome completo do aluno | João Silva |
| `StudentNumber` | Número único do aluno | 2024001 |
| `Listening` | Pontuação em Listening | 85 |
| `Reading` | Pontuação em Reading | 88 |
| `LFM` | Pontuação em Language Form & Meaning | 82 |
| `Total` | Pontuação total | 865 |
| `ListCEFR` | Nível CEFR em Listening | B2 |
| `ReadCEFR` | Nível CEFR em Reading | B2 |
| `LFMCEFR` | Nível CEFR em LFM | B1 |
| `Lexile` | Nível Lexile | 1200L |
| `OSL` | Oral Structured Language | 4-5 |

## 🎯 Mapeamento CEFR

O sistema calcula automaticamente o nível CEFR final baseado na pontuação total:

| Pontuação Total | Nível CEFR |
|-----------------|------------|
| ≥ 865 | B2 |
| 730 - 864 | B1 |
| 625 - 729 | A2 |
| 600 - 624 | A1 |
| < 600 | Below A1 |

## 🛠️ Instalação e Configuração

### Pré-requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### 1. Clonar/Baixar o Projeto
```bash
# Se usando Git
git clone <repository-url>
cd toefl-dashboard

# Ou extrair o arquivo ZIP e navegar para a pasta
```

### 2. Instalar Dependências
```bash
# Instalar todas as dependências
make install

# Ou manualmente
pip install -r requirements.txt
```

### 3. Inicializar Banco de Dados
```bash
# Criar banco e usuários iniciais
make seed

# Ou manualmente
python init_db.py
```

### 4. Executar a Aplicação
```bash
# Iniciar servidor de desenvolvimento
make run

# Ou manualmente
python app.py
```

### 5. Acessar o Sistema
Abra seu navegador e acesse: `http://localhost:5000`

**Credenciais padrão:**
- **Admin**: `admin` / `admin123`
- **Professor**: `professor` / `professor123`

## 📁 Estrutura do Projeto

```
toefl-dashboard/
├── app.py                 # Aplicação principal Flask
├── models.py              # Modelos SQLAlchemy
├── forms.py               # Formulários Flask-WTF
├── requirements.txt       # Dependências Python
├── init_db.py            # Script de inicialização
├── Makefile              # Comandos automatizados
├── pytest.ini           # Configuração de testes
├── README.md             # Este arquivo
├── toefl.db              # Banco SQLite (criado automaticamente)
│
├── services/
│   ├── __init__.py
│   └── importer.py       # Serviço de importação Excel/CSV
│
├── templates/            # Templates HTML
│   ├── base.html         # Template base
│   ├── auth/
│   │   └── login.html    # Página de login
│   ├── dashboard/
│   │   └── index.html    # Dashboard principal
│   ├── upload/
│   │   └── index.html    # Página de upload
│   ├── students/
│   │   ├── index.html    # Lista de alunos
│   │   └── detail.html   # Perfil do aluno
│   ├── classes/
│   │   └── index.html    # Gerenciamento de turmas
│   └── admin/
│       └── index.html    # Administração
│
├── static/               # Arquivos estáticos (criado automaticamente)
│   ├── css/
│   ├── js/
│   └── uploads/          # Arquivos enviados
│
└── tests/                # Testes automatizados
    ├── __init__.py
    ├── test_models.py     # Testes dos modelos
    └── test_importer.py  # Testes do importador
```

## 🔧 Comandos Make Disponíveis

```bash
make help          # Mostra todos os comandos disponíveis
make install       # Instala dependências
make seed          # Inicializa banco de dados
make run           # Inicia servidor de desenvolvimento
make test          # Executa testes
make clean         # Remove arquivos temporários
make reset         # Remove banco e reinicializa (CUIDADO!)
make backup        # Cria backup do banco de dados
make info          # Mostra informações do sistema
```

## 🧪 Testes

O projeto inclui testes automatizados para garantir a qualidade:

```bash
# Executar todos os testes
make test

# Executar testes específicos
python -m pytest tests/test_models.py -v
python -m pytest tests/test_importer.py -v

# Executar com cobertura
python -m pytest --cov=. --cov-report=html
```

## 🎨 Tecnologias Utilizadas

### Backend
- **Flask**: Framework web Python
- **SQLAlchemy**: ORM para banco de dados
- **Flask-Login**: Gerenciamento de sessões
- **Flask-WTF**: Formulários e validação
- **Pandas**: Processamento de dados Excel/CSV
- **OpenPyXL/XlRD**: Leitura de arquivos Excel

### Frontend
- **Bootstrap 5**: Framework CSS responsivo
- **Chart.js**: Gráficos interativos
- **Bootstrap Icons**: Ícones
- **JavaScript**: Interatividade

### Banco de Dados
- **SQLite**: Banco de dados local

### Testes
- **Pytest**: Framework de testes
- **Pytest-Cov**: Cobertura de testes

## 📊 Funcionalidades Detalhadas

### Dashboard Principal (`/dash`)
- Estatísticas gerais do sistema
- Gráfico de distribuição por níveis CEFR
- Gráfico de médias por habilidade (Listening, Reading, LFM)
- Ranking dos 10 melhores alunos
- Lista de alunos que precisam de atenção (Below A1, A1)

### Upload de Dados (`/upload`)
- Seleção de turma de destino
- Upload de arquivos Excel (.xlsx, .xls) ou CSV
- Validação automática de colunas obrigatórias
- Preview dos dados antes da importação
- Processamento com feedback em tempo real
- Histórico de uploads realizados

### Listagem de Alunos (`/alunos`)
- Tabela paginada e ordenável
- Filtros por turma e nível CEFR
- Busca por nome do aluno
- Estatísticas rápidas (total, média, distribuição)
- Exportação para CSV
- Links para perfil individual

### Perfil do Aluno (`/alunos/<id>`)
- Informações completas do aluno
- Gráficos de desempenho por habilidade
- Comparação com média da turma
- Histórico de atualizações
- Badges visuais por nível CEFR

### Gerenciamento de Turmas (`/turmas`)
- Lista de todas as turmas
- Criação de novas turmas
- Edição de turmas existentes
- Estatísticas por turma
- Controle de status (ativo/inativo)

### Administração (`/admin`) - Apenas Administradores
- Gerenciamento de usuários
- Criação de novos usuários
- Edição de permissões
- Ativação/desativação de contas
- Estatísticas do sistema
- Logs de atividade

## 🔒 Segurança

- **Autenticação obrigatória**: Todas as rotas protegidas
- **Controle de acesso**: Diferentes níveis de usuário
- **Validação de arquivos**: Verificação de tipo MIME e tamanho
- **Sanitização de dados**: Limpeza automática de dados importados
- **Proteção CSRF**: Tokens de segurança em formulários
- **Senhas criptografadas**: Hash seguro com Werkzeug

## 🐛 Solução de Problemas

### Erro: "Módulo não encontrado"
```bash
# Verificar se as dependências estão instaladas
make check-deps

# Reinstalar dependências
make install
```

### Erro: "Banco de dados não encontrado"
```bash
# Inicializar o banco
make seed
```

### Erro: "Porta já em uso"
```bash
# Verificar processos na porta 5000
netstat -ano | findstr :5000

# Ou alterar a porta no app.py
```

### Problemas com Upload
- Verificar se as colunas obrigatórias estão presentes
- Confirmar formato do arquivo (Excel ou CSV)
- Verificar tamanho do arquivo (limite padrão: 16MB)
- Verificar permissões da pasta `static/uploads/`

## 📈 Melhorias Futuras

- [ ] Relatórios em PDF
- [ ] Integração com APIs externas
- [ ] Notificações por email
- [ ] Backup automático
- [ ] Interface multi-idioma
- [ ] Análise preditiva
- [ ] Exportação para outros formatos
- [ ] Dashboard mobile dedicado

## 🤝 Contribuição

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

Para dúvidas ou problemas:

1. Verifique a seção de solução de problemas
2. Execute `make info` para informações do sistema
3. Execute os testes com `make test`
4. Consulte os logs da aplicação

---

**TOEFL Junior Dashboard** - Desenvolvido com ❤️ para educadores e estudantes.