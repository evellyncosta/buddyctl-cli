# Copyright 2024 Evellyn
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""LangChain ReAct Agents for buddyctl.

This module provides agent creation functions that orchestrate LLM + tools.

IMPORTANT: The ReAct Agent is a LOCAL framework that:
- Does NOT replace your remote StackSpot agent
- USES your StackSpot agent as the "brain" (LLM)
- ADDS the ability to execute local tools
- ORCHESTRATES the flow: ask LLM → execute tool → ask again → repeat
"""

from typing import List, Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

from .tools import BASIC_TOOLS


def create_buddyctl_agent(
    llm: BaseChatModel,
    tools: Optional[List[BaseTool]] = None,
    verbose: bool = False,
    use_streaming: bool = False
) -> AgentExecutor:
    """
    Create a ReAct Agent LOCAL that orchestrates your remote StackSpot agent + local tools.

    IMPORTANT: This agent does NOT replace your StackSpot agent.
    - The LOCAL agent orchestrates the conversation flow
    - The REMOTE agent (StackSpot) continues doing reasoning and text generation
    - The tools are executed LOCALLY on your computer

    Architecture:
        User → ReAct Agent (LOCAL) → StackSpot Agent (REMOTE)
                    ↓
            Tools (LOCAL): [apply_diff, read_file, ...]

    Args:
        llm: LangChain model (StackSpotChatModel that connects to your remote agent)
        tools: List of local tools (default: BASIC_TOOLS = [read_file, apply_diff])
        verbose: If True, shows the agent's reasoning process
        use_streaming: If True, uses streaming API calls (default: False to avoid timeouts)

    Returns:
        AgentExecutor: Configured agent framework to orchestrate LLM + tools

    Example:
        ```python
        from buddyctl.core.providers import ProviderManager
        from buddyctl.integrations.langchain.agents import create_buddyctl_agent

        # Get LangChain model from provider
        manager = ProviderManager(config)
        llm = manager.get_langchain_model()

        # Create agent with tools (streaming disabled to prevent timeouts)
        agent = create_buddyctl_agent(llm, verbose=True, use_streaming=False)

        # Execute
        result = agent.invoke({"input": "altere calculator.py para 3 números"})
        print(result["output"])
        ```
    """
    if tools is None:
        tools = BASIC_TOOLS  # [read_file, apply_diff]

    # Configure LLM streaming behavior to avoid timeout issues
    # ReAct Agent makes multiple calls to LLM, streaming can cause connection issues
    if hasattr(llm, 'streaming'):
        llm.streaming = use_streaming

    # ReAct Agent Prompt
    # This teaches the LOCAL agent how to use tools
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Você é um assistente de desenvolvimento de código inteligente.

Você tem acesso às seguintes ferramentas que são executadas LOCALMENTE:

{tools}

Nomes das ferramentas: {tool_names}

IMPORTANTE - Regras de uso das ferramentas:

1. **Quando modificar código:**
   - SEMPRE gere um diff unificado no formato git diff
   - SEMPRE use a ferramenta apply_diff após gerar o diff
   - NÃO apenas mostre o diff, aplique-o automaticamente

2. **Quando precisar ler um arquivo:**
   - Use a ferramenta read_file para obter o conteúdo
   - Analise o conteúdo antes de fazer modificações

3. **Formato de resposta:**
   Use EXATAMENTE este formato:

   Thought: Preciso fazer X para responder a pergunta
   Action: nome_da_ferramenta
   Action Input: {{"parametro": "valor"}}
   Observation: resultado da ferramenta
   ... (repita Thought/Action/Action Input/Observation quantas vezes necessário)
   Thought: Agora sei a resposta final
   Final Answer: resposta para o usuário

4. **Exemplos de uso correto:**

   Exemplo 1 - Modificar código:
   ```
   Thought: Preciso ler o arquivo para entender a estrutura atual
   Action: read_file
   Action Input: {{"file_path": "calculator.py"}}
   Observation: [conteúdo do arquivo]
   Thought: Agora vou gerar o diff para as modificações
   Thought: Preciso aplicar o diff automaticamente
   Action: apply_diff
   Action Input: {{"diff_content": "--- a/calculator.py\\n+++ b/calculator.py\\n..."}}
   Observation: Successfully applied diff to calculator.py
   Thought: Modificações aplicadas com sucesso
   Final Answer: ✅ Arquivo calculator.py foi modificado com sucesso!
   ```

   Exemplo 2 - Apenas consultar:
   ```
   Thought: Preciso ler o arquivo para responder
   Action: read_file
   Action Input: {{"file_path": "main.py"}}
   Observation: [conteúdo]
   Thought: Agora posso responder a pergunta
   Final Answer: O arquivo main.py contém...
   ```

LEMBRE-SE: Sempre use apply_diff quando gerar um diff. O usuário espera que as mudanças sejam aplicadas automaticamente!
"""),
        ("user", "{input}"),
        ("assistant", "{agent_scratchpad}")
    ])

    # Create ReAct agent (LOCAL framework)
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )

    # Create AgentExecutor (runs the agent loop)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        handle_parsing_errors=True,
        max_iterations=5,  # Maximum reasoning steps
        return_intermediate_steps=False,  # Don't expose internal steps to user
        max_execution_time=None  # No execution time limit (httpx timeout handles it)
    )
