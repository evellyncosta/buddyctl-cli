"""
StackSpot Chain - Orquestrador simples do padrão two-stage.

Fluxo:
1. Main Agent → resposta em texto livre
2. Judge Agent → analisa e decide tools (JSON)
3. Executa tools localmente se necessário
"""

from typing import List, Dict, Any
from langchain_core.tools import BaseTool
import json
import logging
import re

from .base import BaseChain
from ..chat_model import StackSpotChatModel
from ....ui.message_box import MessageBox


class StackSpotChain(BaseChain):
    """
    Chain simples para StackSpot com Judge Agent pattern.

    Orquestra: Main Agent → Judge Agent → Tools
    """

    def __init__(
        self,
        main_agent_id: str,
        judge_agent_id: str,
        tools: List[BaseTool]
    ):
        """
        Initialize StackSpot Chain.

        Args:
            main_agent_id: StackSpot agent ID for main agent
            judge_agent_id: StackSpot agent ID for judge agent
            tools: Available tools
        """
        super().__init__(tools)

        self.logger = logging.getLogger(__name__)

        # Create models
        self.main_model = StackSpotChatModel(
            agent_id=main_agent_id,
            streaming=False
        )

        self.judge_model = StackSpotChatModel(
            agent_id=judge_agent_id,
            streaming=False
        )

    def invoke(self, user_input: str) -> Dict[str, Any]:
        """
        Execute: Main Agent → Judge Agent → Validate → Tools (with retry)

        Returns:
            {
                "output": str,              # Final response
                "tool_calls_made": List,    # Tools executed
                "iterations": int,          # Number of rounds
                "validation_rounds": int    # Number of correction rounds
            }
        """
        from ..tools import validate_diff_applicability

        MAX_ROUNDS = 3

        self.logger.debug("="*60)
        self.logger.debug("StackSpotChain.invoke() started")

        # Loop state
        round_number = 1
        main_response = None
        decision = None
        validation_error = None

        while round_number <= MAX_ROUNDS:
            self.logger.info(f"--- ROUND {round_number}/{MAX_ROUNDS} ---")

            # 1. Generate response (initial or correction)
            if round_number == 1:
                self.logger.debug("Step 1: Calling Main Agent (initial)")
                response = self.main_model.invoke(user_input)
                main_response = response.content if hasattr(response, 'content') else str(response)
            else:
                self.logger.debug(f"Step 1: Calling Main Agent (correction round {round_number})")
                # Extract file_context from user_input
                file_context = self._extract_file_context(user_input)
                main_response = self.next_round(
                    original_request=user_input,
                    previous_response=main_response,
                    validation_error=validation_error,  # From previous round
                    file_context=file_context,
                    round_number=round_number
                )

            self.logger.debug(f"Main Agent response length: {len(main_response)}")

            # 2. Judge Agent analyzes
            self.logger.debug("Step 2: Calling Judge Agent")
            decision = self._analyze_with_judge(user_input, main_response)
            self.logger.debug(f"Judge decision: needs_tools={decision.get('needs_tools')}")

            # 3. If no tools needed, return directly
            if not decision["needs_tools"]:
                self.logger.debug("No tools needed, returning response")

                # Check if this is due to a parse error
                if decision.get("parse_error"):
                    MessageBox.error(
                        "ERRO: Não foi possível aplicar o diff",
                        "Por favor, aplique as alterações manualmente."
                    )
                    error_message = (
                        f"{main_response}\n\n"
                        f"(Erro interno: falha ao processar resposta do judge - {decision.get('reasoning')})"
                    )
                    return {
                        "output": error_message,
                        "tool_calls_made": [],
                        "iterations": 1,
                        "validation_rounds": round_number - 1,
                        "parse_error": True
                    }

                return {
                    "output": main_response,
                    "tool_calls_made": [],
                    "iterations": 1,
                    "validation_rounds": round_number - 1
                }

            # 4. Extract diff from tool_calls
            self.logger.debug("Step 3: Extracting diff from tool calls")
            diff_content, file_path = self._extract_diff_from_tool_calls(decision["tool_calls"])

            if not diff_content:
                self.logger.warning("No diff found in tool calls")
                return {
                    "output": main_response,
                    "tool_calls_made": decision["tool_calls"],
                    "iterations": 1,
                    "validation_rounds": round_number - 1
                }

            # 5. VALIDATE DIFF BEFORE APPLYING
            self.logger.debug("Step 4: Validating diff applicability")
            is_valid, validation_error = validate_diff_applicability(diff_content, file_path)

            if is_valid:
                # ✅ Valid diff - apply
                self.logger.info(f"✅ Diff validated successfully on round {round_number}")
                self.logger.debug("Step 5: Executing tools")
                tool_results = self._execute_tools(decision["tool_calls"])

                # Log visual de sucesso ao aplicar diff
                MessageBox.success(
                    f"SUCESSO: Diff aplicado com sucesso (round {round_number})",
                    f"Arquivo: {file_path}"
                )

                return {
                    "output": main_response,
                    "tool_calls_made": decision["tool_calls"],
                    "iterations": 1,
                    "validation_rounds": round_number - 1,
                    "tool_results": tool_results
                }
            else:
                # ❌ Invalid diff - retry or fail
                self.logger.warning(f"❌ Diff validation failed on round {round_number}")
                self.logger.warning(f"Validation error: {validation_error}")

                if round_number == MAX_ROUNDS:
                    # Last attempt failed - log visual de erro final
                    MessageBox.error(
                        f"ERRO: Falha ao gerar diff válido após {MAX_ROUNDS} tentativas",
                        f"Erro de validação: {validation_error}"
                    )

                    error_message = (
                        f"Failed to generate valid diff after {MAX_ROUNDS} attempts.\n"
                        f"Final validation error: {validation_error}\n\n"
                        f"Last response from Main Agent:\n{main_response}"
                    )
                    self.logger.error(error_message)
                    return {
                        "output": error_message,
                        "tool_calls_made": [],
                        "iterations": 1,
                        "validation_rounds": round_number,
                        "error": validation_error
                    }
                else:
                    # Try again - log visual de retry de ROUND
                    MessageBox.warning(
                        f"RETRY: Diff inválido, tentando ROUND {round_number + 1}/{MAX_ROUNDS}",
                        f"Razão: {validation_error}"
                    )
                    self.logger.info(f"Retrying with correction (round {round_number + 1})")
                    round_number += 1
                    continue  # Back to start of loop

        # Should never reach here
        self.logger.error("Unexpected: exited validation loop without return")
        return {
            "output": "Internal error: validation loop failed",
            "tool_calls_made": [],
            "iterations": 1,
            "validation_rounds": MAX_ROUNDS
        }

    def _analyze_with_judge(
        self,
        user_input: str,
        assistant_response: str,
        max_judge_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Chama Judge Agent para analisar resposta.

        Implementa retry automático quando JSON é truncado.

        Args:
            user_input: User request
            assistant_response: Main Agent response
            max_judge_retries: Maximum retry attempts for Judge Agent (default: 3)

        Returns:
            {"needs_tools": bool, "tool_calls": List, "reasoning": str}
        """
        # Build tools list
        tools_list = "\n".join([
            f"- {name}: {tool.description}"
            for name, tool in self.tools.items()
        ])

        # Retry loop
        for attempt in range(1, max_judge_retries + 1):
            try:
                # Build prompt (diferente para retry)
                if attempt == 1:
                    # Primeira tentativa: prompt normal
                    prompt = f"""Analyze the assistant's response and decide if tools should be executed.

User Request:
{user_input}

Assistant Response:
{assistant_response}

Available Tools:
{tools_list}"""
                    self.logger.debug("Invoking Judge Agent")
                else:
                    # Retry: prompt MODIFICADO (mais conciso)
                    prompt = f"""Your previous response was truncated. Please analyze again and respond with VALID, COMPLETE JSON only.

CRITICAL: Generate a compact JSON response. If the diff is large, you MUST still include it entirely, but ensure the JSON is properly closed.

User Request:
{user_input}

Assistant Response:
{assistant_response}

Available Tools:
{tools_list}

IMPORTANT: Your response MUST be valid JSON. Close all strings, arrays, and objects properly."""
                    # Log visual de retry
                    MessageBox.warning(
                        f"RETRY: Tentando novamente o Judge Agent ({attempt}/{max_judge_retries})",
                        "Razão: Resposta JSON truncada na tentativa anterior"
                    )
                    self.logger.info(f"Retrying Judge Agent (attempt {attempt}/{max_judge_retries})...")

                response = self.judge_model.invoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                self.logger.debug(f"Judge raw response (first 500 chars): {response_text[:500]}")

                # Parse JSON
                json_text = self._extract_json(response_text)
                self.logger.debug(f"Extracted JSON (first 300 chars): {json_text[:300]}")

                # Try to parse
                decision = json.loads(json_text)
                self.logger.debug(f"Parsed decision: {decision}")

                # ✅ Success!
                if attempt > 1:
                    # Log visual de sucesso no retry
                    MessageBox.success(f"SUCESSO: Judge Agent respondeu corretamente (tentativa {attempt})")
                    self.logger.info(f"✅ Judge Agent succeeded on attempt {attempt}")

                return decision

            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse judge response (attempt {attempt}/{max_judge_retries}): {e}")
                self.logger.debug(f"Failed JSON text: {json_text[:500]}")

                # Se última tentativa, desiste
                if attempt == max_judge_retries:
                    # Log visual de falha total
                    MessageBox.error(
                        f"ERRO: Judge Agent falhou após {max_judge_retries} tentativas",
                        "O diff gerado não será aplicado automaticamente."
                    )
                    self.logger.error(f"❌ Judge Agent failed after {max_judge_retries} attempts")
                    return {
                        "needs_tools": False,
                        "tool_calls": [],
                        "reasoning": f"Parse error after {max_judge_retries} attempts: {e}",
                        "parse_error": True
                    }

                # Senão, retry (volta pro início do loop)
                continue

        # Should never reach here
        return {
            "needs_tools": False,
            "tool_calls": [],
            "reasoning": "Unexpected: retry loop failed",
            "parse_error": True
        }

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from markdown code blocks or plain text.

        No repair logic - just extract and let retry handle failures.
        """
        stripped = text.strip()

        # If text starts with { or [, it's raw JSON (no markdown blocks)
        if stripped.startswith('{') or stripped.startswith('['):
            return stripped

        # Try JSON markdown code blocks (```json)
        match = re.search(r'```json\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If no ```json block, try plain ``` blocks
        match = re.search(r'```\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If no code blocks, return the whole text
        return stripped

    def _extract_diff_from_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> tuple[str | None, str | None]:
        """
        Extract diff content from Judge Agent tool_calls.

        Returns:
            (diff_content, file_path) or (None, None) if not found
        """
        for call in tool_calls:
            if call.get("name") == "apply_diff":
                args = call.get("args", {})
                diff_content = args.get("diff_content")
                # file_path may be in args or extracted from diff
                file_path = args.get("file_path")
                return (diff_content, file_path)

        return (None, None)

    def _extract_file_context(self, user_input: str) -> str:
        """
        Extract file content from user_input (if present).

        Looks for pattern:
        File: path (X lines total)
        ────────────────────────────────────────────
        1 | code
        ...

        Returns:
            Formatted file content or empty string
        """
        # Regex to find file content with line numbers
        pattern = r'File: (.*?) \(\d+ lines total\)\n─+\n(.*?)\n─+'
        match = re.search(pattern, user_input, re.DOTALL)

        if match:
            file_path = match.group(1)
            content = match.group(2)
            return f"File: {file_path}\n────────────────────────────────────────────\n{content}\n────────────────────────────────────────────"

        return ""

    def next_round(
        self,
        original_request: str,
        previous_response: str,
        validation_error: str,
        file_context: str,
        round_number: int
    ) -> str:
        """
        Request correction from Main Agent after validation failure.

        Builds contextualized prompt with:
        - Specific validation error
        - Original user request
        - Previous attempt that failed
        - Current file content (with line numbers)
        - Round number

        Args:
            original_request: Original user request
            previous_response: Previous Main Agent response that failed
            validation_error: Validation error message
            file_context: Formatted file content (with line numbers)
            round_number: Current attempt number (1, 2, 3...)

        Returns:
            New Main Agent response (corrected)

        Example Flow:
            Round 1: User request → Main Agent → Invalid diff
            Round 2: next_round(error="Hunk at line 34...") → Main Agent → Valid diff ✅
        """
        self.logger.info(f"Starting correction round {round_number}")
        self.logger.debug(f"Validation error: {validation_error}")

        # Build correction prompt
        correction_prompt = f"""ROUND {round_number} - DIFF CORRECTION REQUIRED

Your previous diff generation failed validation with the following error:

ERROR: {validation_error}

This means your diff cannot be applied to the actual file. Common causes:
1. Incorrect line numbers in @@ headers
2. Context lines that don't match the actual file content
3. Malformed unified diff syntax

Original user request:
{original_request}

Your previous attempt (REJECTED):
{previous_response}

Current file content with line numbers:
{file_context}

Please generate a CORRECTED diff that:
1. Uses line numbers that match the file content above
2. Includes context lines that EXACTLY match what you see
3. Follows unified diff format strictly (---, +++, @@)

CRITICAL: Copy context lines EXACTLY as shown, including all whitespace.
"""

        # Call Main Agent with correction prompt
        self.logger.debug("Invoking Main Agent for correction")
        response = self.main_model.invoke(correction_prompt)
        corrected_response = response.content if hasattr(response, 'content') else str(response)

        self.logger.debug(f"Main Agent correction response length: {len(corrected_response)}")
        return corrected_response


__all__ = ["StackSpotChain"]
