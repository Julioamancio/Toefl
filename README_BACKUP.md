# Sistema de Backup do TOEFL Dashboard

Este documento descreve como usar o sistema de backup e restore do banco de dados do TOEFL Dashboard.

## Funcionalidades

O sistema oferece duas formas de backup:

1. **Backup Nativo**: Backup específico do tipo de banco (SQLite ou PostgreSQL)
2. **Backup JSON**: Backup universal em formato JSON que funciona entre diferentes tipos de banco

## Scripts Disponíveis

### 1. database_backup.py
Script principal em Python para backup e restore.

### 2. backup_script.bat
Script batch para Windows que facilita o uso do sistema de backup.

## Como Usar

### Backup Automático (Recomendado)

#### Windows:
```bash
# Fazer backup nativo
backup_script.bat backup

# Exportar para JSON
backup_script.bat export
```

#### Linux/Mac:
```bash
# Fazer backup nativo
python database_backup.py backup --file backups/backup_$(date +%Y%m%d_%H%M%S).db

# Exportar para JSON
python database_backup.py export --file backups/export_$(date +%Y%m%d_%H%M%S).json
```

### Backup Manual

```bash
# Backup SQLite/PostgreSQL nativo
python database_backup.py backup --file backups/meu_backup.db

# Backup JSON universal
python database_backup.py export --file backups/meu_backup.json
```

### Restore

#### Windows:
```bash
# Restaurar de backup nativo
backup_script.bat restore backups/toefl_backup_20231201_143022.db

# Importar de JSON
backup_script.bat import backups/toefl_export_20231201_143022.json
```

#### Manual:
```bash
# Restaurar backup nativo
python database_backup.py restore --file backups/meu_backup.db

# Importar JSON
python database_backup.py import --file backups/meu_backup.json
```

## Tipos de Backup

### Backup Nativo
- **SQLite**: Copia o arquivo .db diretamente
- **PostgreSQL**: Usa pg_dump para criar backup completo
- **Vantagens**: Rápido, preserva estrutura exata
- **Desvantagens**: Específico do tipo de banco

### Backup JSON
- **Universal**: Funciona entre SQLite e PostgreSQL
- **Formato**: JSON legível com todos os dados
- **Vantagens**: Portável, legível, funciona entre diferentes bancos
- **Desvantagens**: Maior em tamanho, mais lento

## Estrutura dos Backups

### Diretório
Todos os backups são salvos no diretório `backups/` que é criado automaticamente.

### Nomenclatura Automática
- Backup nativo: `toefl_backup_YYYYMMDD_HHMMSS.db`
- Export JSON: `toefl_export_YYYYMMDD_HHMMSS.json`

## Dados Incluídos no Backup

O sistema faz backup completo de:
- **Estudantes**: Todos os dados dos alunos incluindo notas e níveis CEFR
- **Professores**: Informações dos professores
- **Turmas**: Dados das classes/turmas
- **Notas**: Histórico de avaliações
- **Usuários**: Contas de acesso ao sistema

## Configuração para Produção (Render.com)

### Variáveis de Ambiente Necessárias
```
FLASK_ENV=production
DATABASE_URL=postgresql://user:pass@host:port/dbname
SECRET_KEY=sua_chave_secreta
```

### Backup em Produção
Para fazer backup em produção (PostgreSQL), certifique-se de que:

1. O `pg_dump` está disponível no ambiente
2. A `DATABASE_URL` está configurada corretamente
3. As credenciais têm permissão de leitura/escrita

### Comandos para Produção
```bash
# Backup PostgreSQL
python database_backup.py backup --file backups/prod_backup.dump

# Export JSON (recomendado para produção)
python database_backup.py export --file backups/prod_export.json
```

## Segurança

### Cuidados Importantes
1. **Backups contêm dados sensíveis** - mantenha em local seguro
2. **Restore apaga dados existentes** - sempre confirme antes
3. **Teste backups regularmente** - verifique se podem ser restaurados
4. **Mantenha múltiplas versões** - não dependa de um único backup

### Recomendações
- Faça backup antes de atualizações importantes
- Mantenha backups em locais diferentes (local + nuvem)
- Teste o processo de restore periodicamente
- Use backup JSON para migração entre ambientes

## Troubleshooting

### Erro: "pg_dump não encontrado"
**Solução**: Instale o PostgreSQL client ou adicione ao PATH

### Erro: "Arquivo de backup não encontrado"
**Solução**: Verifique o caminho do arquivo e se existe

### Erro: "Permissão negada"
**Solução**: Verifique permissões do diretório e arquivo

### Erro durante restore: "Tabela já existe"
**Solução**: O script limpa automaticamente, mas em caso de erro, limpe manualmente

## Automação

### Backup Automático Diário
Você pode configurar um cron job (Linux/Mac) ou Tarefa Agendada (Windows):

#### Linux/Mac (crontab):
```bash
# Backup diário às 2:00 AM
0 2 * * * cd /caminho/para/projeto && python database_backup.py export --file backups/daily_$(date +\%Y\%m\%d).json
```

#### Windows (Task Scheduler):
Configure uma tarefa para executar `backup_script.bat export` diariamente.

## Suporte

Para problemas ou dúvidas sobre o sistema de backup:
1. Verifique os logs de erro
2. Confirme as configurações do banco
3. Teste com backup JSON primeiro (mais compatível)
4. Verifique permissões de arquivo e diretório