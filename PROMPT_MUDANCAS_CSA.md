# PROMPT: Mudanças no Cálculo do Listening CSA

## Situação Atual
O sistema atual usa um cálculo por "degraus" onde:
- Diferença ≥ 0 → 5.0 pontos
- Diferença = -1 → 4.0 pontos
- Diferença = -2 → 3.0 pontos
- etc.

## Mudanças Solicitadas

### Para Alunos do 6º Ano (Rótulos 6.1, 6.2, 6.3)
**NOVO CÁLCULO PROPORCIONAL:**
- 200 pontos = 3.0 CSA
- 264 pontos = 5.0 CSA
- Cálculo proporcional entre esses valores
- Abaixo de 200 pontos = proporcionalmente menor que 3.0
- Acima de 264 pontos = 5.0 (teto)

**Fórmula Proporcional para 6º Ano:**
```
se pontuação >= 264: CSA = 5.0
se pontuação >= 200: CSA = 3.0 + ((pontuação - 200) / (264 - 200)) * (5.0 - 3.0)
se pontuação < 200: CSA = (pontuação / 200) * 3.0
```

### Para Alunos do 9º Ano

#### 9.1 - NOVO CÁLCULO PROPORCIONAL:
- **284 pontos = 5.0 CSA** (âncora máxima)
- **0 pontos = 0.0 CSA** (âncora mínima)
- Proporção linear: `CSA = (score / 284) * 5.0`
- Cap máximo de 5.0 CSA
- **IMPORTANTE**: A âncora de 200 pontos = 3.0 CSA é exclusiva do 6° ano, não se aplica ao 9° ano

**Fórmula Proporcional para 9.1:**
```
se pontuação >= 284: CSA = 5.0
senão: CSA = (pontuação / 284) * 5.0
```

#### 9.2 e 9.3 - MANTÉM O CÁLCULO POR DEGRAUS:
- Sistema de degraus baseado na diferença entre CEFR obtido e esperado
- Diferença ≥ 0 → 5.0 pontos
- Diferença = -1 → 4.0 pontos
- Diferença = -2 → 3.0 pontos
- Diferença = -3 → 2.0 pontos
- Diferença = -4 → 1.0 ponto
- Diferença = -5 → 1.0 ponto (A1 STARTER vs B2)
- Diferença < -5 → 0.0 pontos

## Arquivos que Precisam ser Atualizados

1. **listening_csa.py** - Função principal `compute_listening_csa()`
2. **render_auto_fix.py** - Script de correção automática
3. **render_cefr_fix.py** - Script de correção de CEFR
4. **services/importer.py** - Importação de dados
5. **fix_listening_csa_automatic.py** - Script de correção automática
6. **add_and_calculate_listening_csa.py** - Script de recálculo
7. **check_listening_csa_values.py** - Script de verificação
8. **templates/upload/index.html** - Documentação na interface

## Lógica de Implementação

### Função Principal Modificada:
```python
def compute_listening_csa(rotulo_escolar, listening_score):
    # Verificar se é 6º ano (6.1, 6.2, 6.3)
    if rotulo_escolar in [6.1, 6.2, 6.3]:
        # NOVO: Cálculo proporcional para 6º ano
        return calculate_proportional_csa_6th_grade(listening_score)
    else:
        # MANTÉM: Cálculo por degraus para 9º ano
        return calculate_step_based_csa_9th_grade(rotulo_escolar, listening_score)
```

### Função Proporcional para 6º Ano:
```python
def calculate_proportional_csa_6th_grade(listening_score):
    if listening_score is None:
        return {"expected_level": None, "obtained_level": None, "points": 0.0}
    
    # Âncoras: 200 pontos = 3.0 CSA, 264 pontos = 5.0 CSA
    if listening_score >= 264:
        points = 5.0
    elif listening_score >= 200:
        # Proporcional entre 200-264 pontos (3.0-5.0 CSA)
        points = 3.0 + ((listening_score - 200) / (264 - 200)) * (5.0 - 3.0)
    else:
        # Proporcional abaixo de 200 pontos (0.0-3.0 CSA)
        points = (listening_score / 200) * 3.0
    
    # Obter nível CEFR obtido
    obtained_level = get_listening_cefr(listening_score)
    
    return {
        "expected_level": "A2",  # Nível esperado genérico para 6º ano
        "obtained_level": obtained_level,
        "points": round(points, 1)
    }
```

## Validação e Testes

### Casos de Teste para 6º Ano:
- 150 pontos → 2.25 CSA
- 200 pontos → 3.0 CSA
- 232 pontos → 4.0 CSA
- 264 pontos → 5.0 CSA
- 300 pontos → 5.0 CSA (teto)

### Casos de Teste para 9º Ano:
- Mantém todos os testes atuais
- Verifica que o cálculo por degraus continua funcionando

## Impacto nos Scripts Administrativos

1. **Botão de Correção Automática** - Aplicará a nova lógica
2. **Botão de Correção CEFR** - Recalculará com nova fórmula
3. **Importação de Dados** - Usará nova lógica automaticamente
4. **Scripts de Verificação** - Validarão com nova fórmula

## Compatibilidade

- **Dados Existentes**: Todos os CSA existentes serão recalculados
- **Interface**: Nenhuma mudança visual necessária
- **Banco de Dados**: Nenhuma alteração de estrutura necessária
- **Render.com**: Totalmente compatível

Esta mudança torna o sistema mais justo para alunos do 6º ano, usando um cálculo proporcional mais adequado ao nível escolar, enquanto mantém a precisão do sistema de degraus para o 9º ano.

## Status da Implementação

✅ **CONCLUÍDO** - Cálculo proporcional para 6º ano implementado
✅ **CONCLUÍDO** - Cálculo proporcional para 9.1 implementado
✅ **CONCLUÍDO** - Função `compute_listening_csa()` atualizada
✅ **CONCLUÍDO** - Scripts de correção automática atualizados
✅ **CONCLUÍDO** - Testes implementados e validados
✅ **CONCLUÍDO** - Banco de dados corrigido automaticamente
✅ **CONCLUÍDO** - Interface administrativa atualizada

## ✅ RESUMO DAS MUDANÇAS IMPLEMENTADAS

### 1. Cálculo Proporcional para 9.1
- ✅ Implementado cálculo proporcional para estudantes 9.1
- ✅ 0 pontos = 0.0 CSA, 284 pontos = 5.0 CSA
- ✅ Proporção linear: CSA = (score / 284) * 5.0
- ✅ Cap máximo de 5.0 CSA
- ✅ **CORREÇÃO**: Removida âncora de 200 pontos = 3.0 CSA (exclusiva do 6° ano)

### Resumo das Mudanças Implementadas:

1. **listening_csa.py**: 
   - Função principal modificada para usar cálculo proporcional para 6º ano
   - Nova função `calculate_proportional_csa_9_1()` para 9.1
   - Cálculo por degraus mantido para 9.2 e 9.3 com correção para diferença -5

2. **render_auto_fix.py**: Atualizado para usar nova lógica
3. **services/importer.py**: Importação usa nova lógica automaticamente
4. **fix_listening_csa_automatic.py**: Script de correção automática implementado
5. **check_listening_csa_values.py**: Script de verificação atualizado
6. **templates/upload/index.html**: Documentação atualizada na interface

### Validação:
- ✅ Todos os testes passaram (6º ano, 9.1, 9.2, 9.3)
- ✅ Banco de dados corrigido automaticamente
- ✅ Interface administrativa funcionando
- ✅ Cálculos validados com dados reais
- ✅ 9.1 agora usa cálculo proporcional (284 pts = 5.0 CSA)
- ✅ 9.2 e 9.3 mantêm cálculo por degraus corrigido