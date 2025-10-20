# BuddyCtl Agent Prompts

Este diretório contém os prompts para o sistema de Two-Stage Tool Calling (Feature 17).

## Arquitetura

```
User Request
    ↓
┌───────────────────────┐
│   Main Agent          │  ← main_agent.md
│   (Gera resposta)     │
└──────────┬────────────┘
           │ Plain Text Response
           ↓
┌───────────────────────┐
│   Judge Agent         │  ← judge_agent.md
│   (Analisa conteúdo)  │
└──────────┬────────────┘
           │
    ┌──────┴──────┐
    ↓             ↓
[No Tools]   [Execute Tools]
    ↓             ↓
 Return      read_file
Response     apply_diff
```

## Prompts Disponíveis

### 1. main_agent.md
**Objetivo:** Gerar respostas completas e úteis para o usuário

**Tom:** Conversacional e natural

**Formato de saída:** Texto livre (markdown)

**Responsabilidades:**
- Responder perguntas sobre código
- Gerar diffs quando solicitado
- Explicar conceitos de programação
- Fornecer análises e recomendações

**Características:**
- ✅ Não precisa seguir formato rígido (Action:/Input:)
- ✅ Pode especular usando linguagem clara ("probably", "typically")
- ✅ Deve gerar diffs completos em formato unificado
- ✅ Foca em resposta útil, não em chamar tools

**Uso:**
```python
from langchain_core.prompts import ChatPromptTemplate

# Carregar prompt
with open('.doc/prompts/main_agent.md', 'r') as f:
    main_prompt_content = f.read()

# Criar template
prompt = ChatPromptTemplate.from_messages([
    ("system", main_prompt_content),
    ("user", "{input}")
])

# Usar com LLM
response = llm.invoke(prompt.format_messages(input=user_request))
```

---

### 2. judge_agent.md
**Objetivo:** Analisar resposta do Main Agent e decidir se tools devem ser executadas

**Tom:** Analítico e objetivo

**Formato de saída:** JSON estruturado

**Responsabilidades:**
- Analisar CONTEÚDO da resposta (não qualidade)
- Detectar especulação vs dados concretos
- Identificar diffs válidos
- Decidir quais tools executar

**Características:**
- ✅ Análise baseada em padrões (keywords, markers)
- ✅ Decision framework estruturado
- ✅ Sempre retorna JSON válido
- ✅ Prioriza diff > speculation > complete

**Uso:**
```python
from langchain_core.prompts import ChatPromptTemplate
import json

# Carregar prompt
with open('.doc/prompts/judge_agent.md', 'r') as f:
    judge_prompt_content = f.read()

# Criar template
prompt = ChatPromptTemplate.from_messages([
    ("system", judge_prompt_content),
    ("user", "User Request: {user_input}\n\nAssistant Response: {assistant_response}\n\nReturn JSON only:")
])

# Usar com LLM
response = judge_llm.invoke(prompt.format_messages(
    user_input=original_request,
    assistant_response=main_agent_response
))

# Parsear decisão
decision = json.loads(response.content)
# decision = {
#   "needs_tools": true/false,
#   "tool_calls": [...],
#   "reasoning": "..."
# }
```

---

## Tools Disponíveis

### read_file(file_path: str) → str
Lê conteúdo de arquivo texto do disco.

**Judge executa quando:**
- Response especula sobre conteúdo ("probably", "typically")
- Response diz "without seeing the file"
- Usuário pediu para ver arquivo mas response não mostra

**Exemplo:**
```json
{
  "name": "read_file",
  "args": {
    "file_path": "src/calculator.py"
  }
}
```

---

### apply_diff(diff_content: str) → str
Aplica diff unificado a um arquivo existente.

**Judge executa quando:**
- Response CONTÉM diff válido (marcadores ---, +++, @@)
- Usuário pediu modificação e response fornece implementação

**Exemplo:**
```json
{
  "name": "apply_diff",
  "args": {
    "diff_content": "--- a/calculator.py\n+++ b/calculator.py\n@@ -1,3 +1,4 @@\n def add(a, b):\n+    # Add numbers\n     return a + b"
  }
}
```

---

## Padrões de Detecção (Judge Agent)

### Speculation Keywords
- "probably", "likely", "typically", "usually"
- "might", "could", "would"
- "without seeing", "I don't have access"
- "files like this"

### Diff Markers
- Linhas começando com `---` e `+++`
- Headers de hunk: `@@`
- Operações: linhas com `+` (add) e `-` (remove)

### Completeness Indicators
- Dados concretos e específicos
- Código ou conteúdo de arquivo mostrado
- Resposta direta sem especulação

---

## Fluxo Completo de Uso

```python
from buddyctl.integrations.langchain.judge_agent import JudgeAgentExecutor
from buddyctl.integrations.langchain.tools import BASIC_TOOLS

# 1. Criar executor (carrega prompts internamente)
executor = JudgeAgentExecutor(
    llm=main_llm,              # Usa main_agent.md
    judge_llm=judge_llm,       # Usa judge_agent.md
    tools=BASIC_TOOLS,         # [read_file, apply_diff]
    max_iterations=3,
    verbose=True
)

# 2. Executar (faz todo o ciclo automaticamente)
result = executor.invoke("Read calculator.py and add comments")

# 3. Resultado
print(result["output"])           # Resposta final
print(result["tool_calls_made"])  # Tools que foram executadas
print(result["iterations"])       # Quantos ciclos judge fez
```

---

## Exemplo Completo

### Input
```
User: "Modify calculator.py to add type hints"
```

### Stage 1: Main Agent
```
Response: "I'll add type hints to the functions. Here's the diff:

--- a/calculator.py
+++ b/calculator.py
@@ -1,3 +1,3 @@
-def add(a, b):
+def add(a: float, b: float) -> float:
     return a + b
```

### Stage 2: Judge Agent
```json
{
  "needs_tools": true,
  "tool_calls": [
    {
      "name": "apply_diff",
      "args": {
        "diff_content": "--- a/calculator.py\n+++ b/calculator.py\n@@ -1,3 +1,3 @@\n-def add(a, b):\n+def add(a: float, b: float) -> float:\n     return a + b"
      }
    }
  ],
  "reasoning": "Response contains valid unified diff. Extract and apply it."
}
```

### Stage 3: Tool Execution
```
Tool: apply_diff
Result: "Successfully applied diff to calculator.py
- 1 hunk applied
- 1 lines added, 1 lines removed"
```

### Final Output
```
✅ Type hints adicionados com sucesso!

--- a/calculator.py
+++ b/calculator.py
@@ -1,3 +1,3 @@
-def add(a, b):
+def add(a: float, b: float) -> float:
     return a + b

Diff aplicado automaticamente.
```

---

## Boas Práticas

### Para Main Agent Prompt:
- ✅ Seja natural e conversacional
- ✅ Gere diffs completos e bem formatados
- ✅ Use linguagem clara ao especular
- ✅ Foque em resposta útil, não em tools
- ❌ Não tente "fingir" que executou tools
- ❌ Não gere diffs parciais

### Para Judge Agent Prompt:
- ✅ Seja objetivo e analítico
- ✅ Base decisões em padrões detectáveis
- ✅ Sempre retorne JSON válido
- ✅ Extraia conteúdo completo (diffs inteiros)
- ❌ Não julgue qualidade da resposta
- ❌ Não adivinhe file paths
- ❌ Não execute tools desnecessariamente

---

## Versionamento

**Versão Atual:** 1.0
**Feature:** 17 - Two-Stage Tool Calling
**Data:** 2025-10-17

### Changelog

#### v1.0 (2025-10-17)
- ✅ Prompt inicial para Main Agent
- ✅ Prompt inicial para Judge Agent
- ✅ Documentação de 2 tools (read_file, apply_diff)
- ✅ Exemplos completos de uso
- ✅ Padrões de detecção documentados

---

## Referências

- **Feature 17 (Arquitetura):** `.doc/feature-17-unified-tool-calling-abstraction.md`
- **Feature 18 (Implementação):** `.doc/feature-18-judge-agent-integration.md`
- **Tools Implementation:** `buddyctl/integrations/langchain/tools.py`
- **Judge Executor:** `buddyctl/integrations/langchain/judge_agent.py` (a implementar em Feature 18)

---

## Contribuindo

Para adicionar novas tools:

1. Implementar tool em `tools.py` com decorator `@tool`
2. Atualizar seção "Available Tools" em `judge_agent.md`
3. Adicionar exemplos de detecção e uso
4. Atualizar este README com a nova tool
5. Testar com Judge Agent

Para modificar prompts:

1. Editar arquivo `.md` correspondente
2. Testar com casos reais
3. Atualizar exemplos se necessário
4. Documentar mudanças no changelog
5. Incrementar versão
