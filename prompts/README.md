# BuddyCtl Agent Prompts

Este diretório contém o prompt para o sistema de SEARCH/REPLACE (single-stage tool calling).

## Arquitetura

```
User Request
    ↓
┌───────────────────────┐
│   Main Agent          │  ← main_agent.md
│   (Gera resposta com) │
│   SEARCH/REPLACE      │
└──────────┬────────────┘
           │ Natural Response + SEARCH/REPLACE blocks
           ↓
┌───────────────────────┐
│   Local Validator     │
│   (Instant check)     │
└──────────┬────────────┘
           │
    ┌──────┴──────┐
    ↓             ↓
[Valid]     [Invalid]
    ↓             ↓
 Apply         Retry
Blocks     (with error)
```

## Prompts Disponíveis

### main_agent.md
**Objetivo:** Gerar respostas completas com blocos SEARCH/REPLACE para modificações de código

**Tom:** Conversacional e natural

**Formato de saída:** Texto livre (markdown) com blocos SEARCH/REPLACE quando necessário

**Responsabilidades:**
- Responder perguntas sobre código
- Gerar blocos SEARCH/REPLACE quando solicitado modificações
- Explicar conceitos de programação
- Fornecer análises e recomendações

**Características:**
- ✅ Linguagem natural e conversacional
- ✅ Usa blocos SEARCH/REPLACE com marcadores únicos (`<<<<<<< SEARCH`, `=======`, `>>>>>>> REPLACE`)
- ✅ SEARCH deve corresponder exatamente ao conteúdo do arquivo (incluindo espaços)
- ✅ Pode gerar múltiplos blocos SEARCH/REPLACE em uma resposta
- ✅ Foca em resposta útil com explicações claras

**Formato SEARCH/REPLACE:**
```
<<<<<<< SEARCH
[exact text to find in file]
=======
[new text to replace with]
>>>>>>> REPLACE
```

**Uso:**
```python
from langchain_core.prompts import ChatPromptTemplate

# Carregar prompt
with open('prompts/main_agent.md', 'r') as f:
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

## Padrão SEARCH/REPLACE

### Vantagens
- **Simples**: Um único agente, uma única chamada de API
- **Rápido**: Validação local instantânea (sem API call adicional)
- **Confiável**: ~90-95% taxa de sucesso
- **Claro**: Marcadores únicos que não aparecem em código normal
- **Retry**: Até 3 tentativas com feedback de erro detalhado

### Local Validator
O validador local verifica instantaneamente se:
1. O texto SEARCH existe no arquivo
2. O texto SEARCH aparece exatamente uma vez (é único)
3. Todos os blocos são válidos antes de aplicar

**Processo:**
```python
# 1. Extrai blocos SEARCH/REPLACE da resposta
blocks = extract_search_replace_blocks(response)

# 2. Valida cada bloco (instant)
with open(file_path, 'r') as f:
    file_content = f.read()

for block in blocks:
    if block.search not in file_content:
        return (False, f"SEARCH text not found: {block.search[:50]}...")

    if file_content.count(block.search) > 1:
        return (False, f"SEARCH text appears {count} times - not unique")

# 3. Aplica se todos válidos
return (True, None)
```

### Retry Logic
Quando validação falha, o sistema:
1. Mostra qual bloco falhou e por quê
2. Envia contexto completo do arquivo com números de linha
3. Pede para o agente corrigir usando texto exato do arquivo
4. Até 3 rounds de retry

**Taxa de sucesso:**
- 1ª tentativa: ~70-80%
- Após retry: ~90-95%

---

## Tools Disponíveis

### read_file(file_path: str) → str
Lê conteúdo de arquivo texto do disco.

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

## Fluxo Completo de Uso

```python
from buddyctl.integrations.langchain.chains.stackspot_chain import StackSpotChain
from buddyctl.integrations.langchain.tools import read_file

# 1. Criar chain (carrega prompts internamente)
chain = StackSpotChain(
    main_agent_id="your_agent_id",
    tools=[read_file]
)

# 2. Executar (faz todo o ciclo automaticamente)
result = chain.invoke("Add comments to calculator.py")

# 3. Resultado
print(result["output"])           # Resposta final
print(result["blocks_applied"])   # Número de blocos aplicados
print(result["validation_rounds"]) # Número de rounds (0 = sucesso na 1ª)
```

---

## Exemplo Completo

### Input
```
User: "Add type hints to calculator.py"
```

### Stage 1: Main Agent
```
I'll add type hints to the functions. Here's the change:

<<<<<<< SEARCH
def add(a, b):
    return a + b
=======
def add(a: float, b: float) -> float:
    return a + b
>>>>>>> REPLACE

This adds type hints for float parameters and return value.
```

### Stage 2: Local Validation
```python
# Instant check (no API call)
is_valid = validate_search_replace_blocks(blocks, "calculator.py")
# Result: (True, None) - texto encontrado exatamente uma vez
```

### Stage 3: Apply
```
✅ Successfully applied 1 SEARCH/REPLACE block to calculator.py
```

### Final Output
```
✅ Type hints adicionados com sucesso!

<<<<<<< SEARCH
def add(a, b):
    return a + b
=======
def add(a: float, b: float) -> float:
    return a + b
>>>>>>> REPLACE

This adds type hints for float parameters and return value.

Changes applied automatically.
```

---

## Boas Práticas

### Para Main Agent Prompt:
- ✅ Seja natural e conversacional
- ✅ Gere blocos SEARCH/REPLACE completos
- ✅ SEARCH deve corresponder EXATAMENTE ao arquivo (incluindo indentação)
- ✅ Use linguagem clara nas explicações
- ✅ Foque em resposta útil com contexto
- ❌ Não tente "fingir" que executou tools
- ❌ Não gere blocos parciais ou incompletos

---

## Versionamento

**Versão Atual:** 2.0
**Feature:** Single-stage SEARCH/REPLACE Pattern (Fix-26)
**Data:** 2025-10-23

### Changelog

#### v2.0 (2025-10-23)
- ✅ Migrado para padrão SEARCH/REPLACE (single-stage)
- ✅ Removido Judge Agent (não mais necessário)
- ✅ Validação local instantânea
- ✅ 50% mais rápido, 60% menos tokens
- ✅ Taxa de sucesso: ~90-95%

#### v1.0 (2025-10-17)
- ✅ Prompt inicial para Main Agent
- ✅ Two-stage pattern com Judge Agent (deprecado)

---

## Referências

- **Fix 26 (Migração):** `.doc/fix-26-search-replace-migration.md`
- **Feature 17 (Arquitetura):** `.doc/feature-17-unified-tool-calling-abstraction.md`
- **Tools Implementation:** `buddyctl/integrations/langchain/tools.py`
- **StackSpot Chain:** `buddyctl/integrations/langchain/chains/stackspot_chain.py`
- **Architecture:** `ARCHITECTURE.md`

---

## Contribuindo

Para modificar o prompt:

1. Editar `main_agent.md`
2. Testar com casos reais
3. Atualizar exemplos se necessário
4. Documentar mudanças no changelog
5. Incrementar versão
