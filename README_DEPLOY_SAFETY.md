# Estratégia de Deploy Seguro (GitHub + Render)

Objetivo: permitir testar atualizações no Render.com sem quebrar nada que já está funcionando.

## Branches

- `main`: produção (protegido). Não fazer push direto.
- `staging`: homologação. Deploy automático para o Render Staging.
- `feature/*`: desenvolvimento das features.

## Workflows (GitHub Actions)

- `CI` (`.github/workflows/ci.yml`): roda em PRs para `main` e `staging` e em push para `staging`.
  - Instala deps, roda `flake8`, `pytest` e valida a factory `create_app('testing')`.
- `Deploy Staging` (`.github/workflows/deploy-staging.yml`):
  - Gatilho: push para `staging` ou manual.
  - Ação: chama o Deploy Hook do serviço Staging no Render.
- `Deploy Production` (`.github/workflows/deploy-prod.yml`):
  - Gatilho: push de tags `v*.*.*` (ex.: `v1.2.0`) ou manual.
  - Ação: chama o Deploy Hook do serviço de Produção.

## Configurar Secrets do Repositório

No GitHub (`Settings` → `Secrets and variables` → `Actions`), cadastrar:

- `RENDER_DEPLOY_HOOK_URL_STAGING`: URL do Deploy Hook do serviço Staging.
- `RENDER_DEPLOY_HOOK_URL_PROD`: URL do Deploy Hook do serviço de Produção.

Como obter no Render:
1. Abra o serviço → `Settings` → `Deploy Hooks`.
2. Copie a URL e cole no secret correspondente.

## Proteção do `main` (GitHub)

Em `Settings` → `Branches` → `Branch protection rules`:
- Habilitar "Require a pull request before merging".
- Exigir pelo menos 1 review.
- Marcar "Require status checks to pass" e selecionar o check `CI`.
- Bloquear pushes diretos e force-push.

## Fluxo de Trabalho Recomendado

1. Crie sua feature:
   ```bash
   git checkout -b feature/minha-melhoria
   # ... faça os commits
   git push origin feature/minha-melhoria
   ```
2. Abra um PR de `feature/*` → `staging`. O `CI` roda.
3. Faça merge em `staging` → dispara o Deploy Staging no Render.
4. Valide no ambiente Staging.
5. Abra PR de `staging` → `main` (ou `main` via release tag):
   - Opção A (tag):
     ```bash
     git checkout main
     git merge --no-ff staging
     git tag -a v1.0.0 -m "Release v1.0.0"
     git push origin main --tags
     ```
     O push da tag aciona o Deploy Production.
   - Opção B (manual): use `Actions` → `Deploy Production` → `Run workflow`.

## Rollback Seguro

- Use o histórico de tags: redeploy a tag estável anterior pelo workflow de produção.
- No Render, é possível usar "Rollback" no serviço para retornar ao deploy anterior.

## Observações de Produção

- Health check: `GET /health/db` (já configurado no `render.yaml`).
- Variáveis de ambiente: ver `README_DEPLOY.md` / `render.yaml`.
- Backup: há rotas administrativas e scripts (`database_backup.py`).

## Dúvidas

Se precisar, abra uma issue ou me avise para ajustarmos o fluxo.