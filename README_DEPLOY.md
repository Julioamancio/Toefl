# Deploy no Render.com - TOEFL Dashboard

Este guia explica como fazer o deploy da aplicação TOEFL Dashboard no Render.com.

## Pré-requisitos

1. Conta no [Render.com](https://render.com)
2. Repositório Git com o código da aplicação
3. Código preparado para produção (já configurado neste projeto)

## Arquivos de Configuração Criados

### 1. `config.py`
- Configurações separadas por ambiente (desenvolvimento, produção, teste)
- Suporte a PostgreSQL em produção
- Configurações de segurança aprimoradas

### 2. `wsgi.py`
- Ponto de entrada WSGI para o Gunicorn
- Configurado para ambiente de produção

### 3. `render.yaml`
- Configuração específica para o Render.com
- Define serviço web e banco de dados PostgreSQL
- Variáveis de ambiente necessárias

### 4. `init_production.py`
- Script para inicializar o banco de dados em produção
- Cria usuário admin padrão

### 5. `Dockerfile` e `.dockerignore`
- Para containerização (opcional no Render)
- Otimizado para produção

## Passos para Deploy

### 1. Preparar o Repositório
```bash
git add .
git commit -m "Preparar para deploy no Render.com"
git push origin main
```

### 2. Criar Serviço no Render

1. Acesse [Render.com](https://render.com) e faça login
2. Clique em "New +" → "Web Service"
3. Conecte seu repositório Git
4. Configure o serviço:
   - **Name**: `toefl-dashboard`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT wsgi:application`

### 3. Configurar Variáveis de Ambiente

No painel do Render, adicione as seguintes variáveis de ambiente:

- `FLASK_ENV`: `production`
- `SECRET_KEY`: (gere uma chave secreta forte)
- `DATABASE_URL`: (será preenchida automaticamente quando criar o banco)
- `ADMIN_PASSWORD`: (senha para o usuário admin inicial)

### 4. Criar Banco de dados PostgreSQL

1. No Render, clique em "New +" → "PostgreSQL"
2. Configure:
   - **Name**: `toefl-db`
   - **Database Name**: `toefl_dashboard`
   - **User**: `toefl_user`

### 5. Conectar Banco ao Serviço Web

1. No serviço web, vá em "Environment"
2. Adicione a variável `DATABASE_URL` com o valor da connection string do PostgreSQL

### 6. Inicializar Banco de Dados

Após o primeiro deploy, execute o script de inicialização:

```bash
# No console do Render ou via SSH
python init_production.py
```

## Configurações Importantes

### Uploads de Arquivos
- Em produção, os uploads são salvos em `/tmp/uploads`
- Para persistência, considere usar um serviço de storage externo (AWS S3, etc.)

### Segurança
- HTTPS habilitado automaticamente no Render
- Cookies seguros configurados
- CSRF protection ativado

### Monitoramento
- Logs disponíveis no painel do Render
- Health check configurado no Dockerfile

## Variáveis de Ambiente Necessárias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `FLASK_ENV` | Ambiente da aplicação | `production` |
| `SECRET_KEY` | Chave secreta do Flask | `sua-chave-super-secreta` |
| `DATABASE_URL` | URL do PostgreSQL | `postgresql://user:pass@host/db` |
| `ADMIN_PASSWORD` | Senha do admin inicial | `senha-segura-123` |

## Comandos Úteis

### Executar migrações
```bash
python init_production.py
```

### Verificar logs
```bash
# No painel do Render, aba "Logs"
```

### Backup do banco
```bash
# Use as ferramentas do Render para backup automático
```

## Troubleshooting

### Erro de conexão com banco
- Verifique se a `DATABASE_URL` está correta
- Confirme que o banco PostgreSQL está rodando

### Erro 500
- Verifique os logs no painel do Render
- Confirme se todas as variáveis de ambiente estão configuradas

### Uploads não funcionam
- Verifique se a pasta `/tmp/uploads` tem permissões corretas
- Considere implementar storage externo para persistência

## Próximos Passos

1. Configurar domínio customizado (opcional)
2. Implementar storage externo para uploads
3. Configurar backup automático do banco
4. Implementar monitoramento e alertas
5. Configurar CI/CD para deploys automáticos