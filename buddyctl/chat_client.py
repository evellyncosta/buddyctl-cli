"""Chat client for StackSpot agent communication with SSE streaming support."""

import json
import time
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
import httpx

from .auth import StackSpotAuth, AuthenticationError
from .config import BuddyConfig
from .api_client import APIClient


@dataclass
class ChatRequest:
    """Chat request data model."""
    streaming: bool = True
    user_prompt: str = ""
    stackspot_knowledge: bool = False
    return_ks_in_response: bool = True


@dataclass 
class ChatResponse:
    """Chat response data model."""
    message: str = ""
    stop_reason: str = ""
    error: Optional[str] = None


class ChatClient:
    """Client for chat communication with StackSpot agents via SSE streaming."""
    
    def __init__(self, auth: Optional[StackSpotAuth] = None, config: Optional[BuddyConfig] = None):
        self.auth = auth or StackSpotAuth()
        self.config = config or BuddyConfig()
        self.api_client = APIClient(self.auth, self.config)
        self.timeout = 300  # 5 minutes
    
    def chat_stream(self, agent_id: str, prompt: str, on_message: Callable[[str], None]) -> None:
        """
        Send a chat message and stream the response via SSE.
        
        Args:
            agent_id: The StackSpot agent ID
            prompt: User message to send
            on_message: Callback function called for each chunk of response
            
        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If HTTP request fails
            ValueError: If agent_id is invalid
        """
        if not agent_id or not agent_id.strip():
            raise ValueError("Agent ID is required")
        
        if not prompt or not prompt.strip():
            raise ValueError("Prompt is required")
        
        # Create request payload
        request = ChatRequest(
            streaming=True,
            user_prompt=prompt.strip(),
            stackspot_knowledge=False,
            return_ks_in_response=True
        )
        
        # Build URL using v1 agent endpoint (matching Go code)
        url = self.api_client.build_url(f"/v1/agent/{agent_id}/chat")
        
        # Prepare headers for SSE
        headers = self.api_client.get_auth_headers()
        headers.update({
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        })
        
        # Send streaming request
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream(
                "POST",
                url,
                json=request.__dict__,
                headers=headers
            ) as response:
                
                if response.status_code != 200:
                    # For streaming response, we need to read the content first
                    error_content = ""
                    try:
                        # Read error content from stream
                        for chunk in response.iter_bytes():
                            error_content += chunk.decode('utf-8', errors='ignore')
                    except Exception:
                        error_content = f"Unable to read error details (status {response.status_code})"

                    # Handle specific error codes
                    if response.status_code == 403:
                        error_msg = "Forbidden - Check your API credentials and permissions"
                        if error_content:
                            error_msg += f": {error_content}"
                    elif response.status_code == 401:
                        error_msg = "Unauthorized - Authentication failed. Try refreshing your token"
                    elif response.status_code == 404:
                        error_msg = f"Agent not found (ID: {agent_id})"
                    else:
                        error_msg = error_content or f"HTTP {response.status_code}"

                    raise httpx.HTTPStatusError(
                        f"API error (status {response.status_code}): {error_msg}",
                        request=response.request,
                        response=response
                    )
                
                # Process SSE stream
                self._process_sse_stream(response, on_message)
    
    def _process_sse_stream(self, response: httpx.Response, on_message: Callable[[str], None]) -> None:
        """
        Process Server-Sent Events stream.
        
        Args:
            response: The streaming HTTP response
            on_message: Callback for each message chunk
        """
        for line in response.iter_lines():
            if not line:
                continue
                
            line = line.strip()
            
            # SSE format: "data: {json}" or "data: [DONE]"
            if line.startswith("data: "):
                data = line[6:]  # Remove "data: " prefix
                
                # Skip ping/heartbeat messages
                if not data or data == ":":
                    continue
                
                # Handle end of stream
                if data == "[DONE]":
                    break
                
                try:
                    # Parse JSON response
                    response_data = json.loads(data)
                    chat_response = ChatResponse(
                        message=response_data.get("message", ""),
                        stop_reason=response_data.get("stop_reason", ""),
                        error=response_data.get("error")
                    )
                    
                    # Send message chunk if available
                    if chat_response.message:
                        on_message(chat_response.message)
                    
                    # Check for stop condition
                    if chat_response.stop_reason and chat_response.stop_reason != "null":
                        break
                        
                    # Handle errors
                    if chat_response.error:
                        on_message(f"\n❌ Error: {chat_response.error}")
                        break
                        
                except json.JSONDecodeError:
                    # If we can't parse as JSON, treat as raw text
                    on_message(data)
    
    def chat_non_stream(self, agent_id: str, prompt: str) -> ChatResponse:
        """
        Send a non-streaming chat message (fallback method).
        
        Args:
            agent_id: The StackSpot agent ID
            prompt: User message to send
            
        Returns:
            ChatResponse with the complete response
            
        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If HTTP request fails
            ValueError: If agent_id is invalid
        """
        if not agent_id or not agent_id.strip():
            raise ValueError("Agent ID is required")
        
        if not prompt or not prompt.strip():
            raise ValueError("Prompt is required")
        
        # Create request payload
        request = ChatRequest(
            streaming=False,
            user_prompt=prompt.strip(),
            stackspot_knowledge=False,
            return_ks_in_response=True
        )
        
        # Build URL using v1 agent endpoint (matching Go code)
        url = self.api_client.build_url(f"/v1/agent/{agent_id}/chat")
        
        # Send request
        headers = self.api_client.get_auth_headers()
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=request.__dict__, headers=headers)
            
            if response.status_code != 200:
                error_text = response.text

                # Handle specific error codes
                if response.status_code == 403:
                    error_msg = "Forbidden - Check your API credentials and permissions"
                    if error_text:
                        error_msg += f": {error_text}"
                elif response.status_code == 401:
                    error_msg = "Unauthorized - Authentication failed. Try refreshing your token"
                elif response.status_code == 404:
                    error_msg = f"Agent not found (ID: {agent_id})"
                else:
                    error_msg = error_text or f"HTTP {response.status_code}"

                raise httpx.HTTPStatusError(
                    f"API error (status {response.status_code}): {error_msg}",
                    request=response.request,
                    response=response
                )
            
            response_data = response.json()
            return ChatResponse(
                message=response_data.get("message", ""),
                stop_reason=response_data.get("stop_reason", ""),
                error=response_data.get("error")
            )
    
    def validate_agent(self, agent_id: str) -> bool:
        """
        Validate if an agent ID exists and is accessible.
        
        Args:
            agent_id: The agent ID to validate
            
        Returns:
            True if agent is valid, False otherwise
        """
        try:
            # Try a minimal request to check agent existence
            url = self.api_client.build_agent_url("/chat", agent_id)
            headers = self.api_client.get_auth_headers()
            
            test_request = ChatRequest(
                streaming=False,
                user_prompt="test",
                stackspot_knowledge=False,
                return_ks_in_response=False
            )
            
            with httpx.Client(timeout=30) as client:
                response = client.post(url, json=test_request.__dict__, headers=headers)
                
                # Agent exists if we don't get 404
                if response.status_code == 404:
                    return False
                
                # Consider 200 and 400 as valid (400 might be empty prompt)
                return response.status_code in [200, 400]
                
        except Exception:
            return False