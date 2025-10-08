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

"""Utilities for LangChain integration."""

from typing import List
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)


def convert_langchain_messages_to_stackspot(messages: List[BaseMessage]) -> str:
    """Convert LangChain messages to StackSpot API format.
    
    StackSpot API expects a single 'user_prompt' string, not a message array.
    This function converts LangChain message history into a formatted string
    that preserves the conversation context.
    
    The conversion follows this pattern:
    - SystemMessage → "System: {content}\\n\\n"
    - HumanMessage → "User: {content}\\n\\n"
    - AIMessage → "Assistant: {content}\\n\\n"
    
    Args:
        messages: List of LangChain messages
        
    Returns:
        Formatted string with complete conversation history
        
    Example:
        >>> from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        >>> messages = [
        ...     SystemMessage(content="You are a Python expert"),
        ...     HumanMessage(content="Explain decorators"),
        ...     AIMessage(content="Decorators are functions that..."),
        ...     HumanMessage(content="Give me an example")
        ... ]
        >>> prompt = convert_langchain_messages_to_stackspot(messages)
        >>> print(prompt)
        System: You are a Python expert
        
        User: Explain decorators
        
        Assistant: Decorators are functions that...
        
        User: Give me an example
    """
    parts = []
    
    for message in messages:
        if isinstance(message, SystemMessage):
            parts.append(f"System: {message.content}")
        elif isinstance(message, HumanMessage):
            parts.append(f"User: {message.content}")
        elif isinstance(message, AIMessage):
            parts.append(f"Assistant: {message.content}")
        else:
            # Fallback for unknown message types
            # This ensures compatibility with future LangChain message types
            parts.append(f"Unknown: {message.content}")
    
    # Join all parts with double newline for readability
    return "\n\n".join(parts)