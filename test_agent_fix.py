#!/usr/bin/env python3
"""Test script to validate the httpx timeout fix for ReAct Agent."""

import sys
from buddyctl.core.config import BuddyConfig
from buddyctl.core.auth import StackSpotAuth
from buddyctl.integrations.langchain.agents import create_buddyctl_agent
from buddyctl.core.providers import ProviderManager

def main():
    print("=" * 60)
    print("Testing ReAct Agent with httpx timeout fix")
    print("=" * 60)
    print()

    # Setup
    config = BuddyConfig()
    auth = StackSpotAuth()
    provider_manager = ProviderManager(config, auth=auth)

    # Check auth
    auth_status = auth.get_auth_status()
    if not auth_status["authenticated"]:
        print("❌ Not authenticated. Please check credentials.")
        return 1

    print(f"✅ Authenticated (Realm: {auth_status['realm']})")
    print()

    # Get LangChain model
    try:
        llm = provider_manager.get_langchain_model()
        print(f"✅ LangChain model loaded: {llm._llm_type}")
        print(f"   Agent ID: {llm.agent_id}")
        print(f"   Streaming: {llm.streaming}")
        print()
    except Exception as e:
        print(f"❌ Failed to load LangChain model: {e}")
        return 1

    # Create agent
    try:
        agent = create_buddyctl_agent(llm, verbose=True)
        print("✅ ReAct Agent created")
        print()
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        return 1

    # Test 1: Simple query (should use 1-2 calls)
    print("=" * 60)
    print("Test 1: Simple query")
    print("=" * 60)
    print()

    try:
        print("Query: 'Responda apenas: OK'")
        print()
        result = agent.invoke({"input": "Responda apenas: OK"})
        print()
        print(f"✅ Result: {result['output']}")
        print()
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        print()
        return 1

    # Test 2: Query that might trigger tool use
    print("=" * 60)
    print("Test 2: Query with potential tool use")
    print("=" * 60)
    print()

    try:
        print("Query: 'Liste os passos para criar um arquivo Python'")
        print()
        result = agent.invoke({"input": "Liste os passos para criar um arquivo Python"})
        print()
        print(f"✅ Result: {result['output'][:200]}...")
        print()
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        print()
        return 1

    print("=" * 60)
    print("✅ All tests passed! Agent is working correctly.")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
