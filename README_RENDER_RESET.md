# 🔄 Guia de Reset e Importação do Banco de Dados no Render

Este guia explica como limpar completamente o banco de dados do Render e importar um backup limpo.

## 📋 Ferramentas Disponíveis

### 1. `render_database_reset.py` - Reset Completo
Script para limpar completamente o banco de dados e opcionalmente importar backup.

### 2. `render_backup_import.py` - Importação de Backup
Script dedicado apenas para importar dados de backup.

### 3. `init_render.py` - Inicialização Automática
Script que executa automaticamente no deploy, com suporte a reset e importação via variáveis de ambiente.

## 🚀 Como Usar

### Opção 1: Reset via Variáveis de Ambiente (Recomendado)

1. **No painel do Render**, vá em Environment Variables
2. **Adicione as variáveis**:
   - `RESET_DATABASE=true` (para limpar o banco)
   - `IMPORT_BACKUP=true` (para importar backup após limpeza)
3. **Faça um redeploy** manual ou push para o GitHub

### Opção 2: Script Manual no Console do Render

1. **Acesse o Shell do Render**
2. **Para reset completo**:
   ```bash
   python render_database_reset.py --reset
   ```

3. **Para reset + importar backup**:
   ```bash
   python render_database_reset.py --reset --import-backup
   ```

4. **Para apenas importar backup**:
   ```bash
   python render_backup_import.py
   ```

### Opção 3: Teste Local

1. **Reset completo local**:
   ```bash
   python render_database_reset.py --reset --import-backup
   ```

2. **Apenas correção de asteriscos**:
   ```bash
   python render_database_reset.py --fix-asterisks
   ```

## 📁 Preparação do Backup

1. **Coloque o arquivo de backup** na pasta `backups/`
2. **O arquivo deve estar em formato JSON** com a estrutura:
   ```json
   {
     "students": [...],
     "teachers": [...],
     "classes": [...],
     "computed_levels": [...]
   }
   ```

3. **Se não especificar arquivo**, o script usa automaticamente o mais recente da pasta `backups/`

## 🔧 Funcionalidades Automáticas

### ✅ Limpeza de Asteriscos
- Remove automaticamente asteriscos dos campos CEFR durante importação
- Recalcula o `General_CEFR` corretamente
- Aplica correções em tempo real

### ✅ Verificação de Duplicatas
- Evita importar dados duplicados
- Verifica por email e nome antes de inserir
- Mantém integridade dos dados

### ✅ Logs Detalhados
- Mostra progresso em tempo real
- Indica quantos registros foram processados
- Reporta erros específicos

## 🎯 Cenários de Uso

### Cenário 1: Banco Corrompido
```bash
# Limpar tudo e importar backup limpo
RESET_DATABASE=true
IMPORT_BACKUP=true
```

### Cenário 2: Apenas Asteriscos
```bash
# Apenas corrigir asteriscos sem reset
python render_database_reset.py --fix-asterisks
```

### Cenário 3: Importar Dados Novos
```bash
# Importar sem limpar dados existentes
python render_backup_import.py backup_novo.json
```

### Cenário 4: Reset Completo Manual
```bash
# Via console do Render
python render_database_reset.py --reset --import-backup
```

## ⚠️ Avisos Importantes

1. **BACKUP SEMPRE**: Faça backup antes de qualquer reset
2. **TESTE LOCAL**: Teste o processo localmente primeiro
3. **VARIÁVEIS DE AMBIENTE**: Remova as variáveis após o reset para evitar resets acidentais
4. **LOGS**: Monitore os logs durante o processo

## 🔍 Verificação Pós-Reset

Após o reset, verifique:

1. **Tabelas criadas**: Todas as tabelas devem estar presentes
2. **Dados importados**: Contagem de registros deve estar correta
3. **Asteriscos removidos**: Nenhum campo CEFR deve conter asteriscos
4. **General_CEFR calculado**: Todos os estudantes devem ter General_CEFR válido

## 🆘 Solução de Problemas

### Problema: "Nenhum backup encontrado"
**Solução**: Coloque o arquivo .json na pasta `backups/`

### Problema: "Erro de conexão com banco"
**Solução**: Verifique as variáveis de ambiente do PostgreSQL

### Problema: "Dados duplicados"
**Solução**: Use `RESET_DATABASE=true` para limpar antes da importação

### Problema: "Asteriscos ainda presentes"
**Solução**: Execute `python render_database_reset.py --fix-asterisks`

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs do Render
2. Teste o processo localmente
3. Verifique se o arquivo de backup está correto
4. Confirme as variáveis de ambiente