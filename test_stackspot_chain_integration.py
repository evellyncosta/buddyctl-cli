#!/usr/bin/env python3
"""
Test StackSpotChain integration with SEARCH/REPLACE pattern.

This script simulates the complete flow:
1. Main Agent generates SEARCH/REPLACE blocks
2. Extract blocks
3. Local validation
4. Apply changes
"""

import sys
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from buddyctl.core.config import BuddyConfig
from buddyctl.core.providers.adapters.stackspot import StackSpotAdapter
from buddyctl.integrations.langchain.tools import read_file, apply_diff

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("="*60)
    logger.info("StackSpotChain Integration Test - SEARCH/REPLACE Pattern")
    logger.info("="*60)

    # 1. Setup
    logger.info("\n📋 Step 1: Setup")
    config = BuddyConfig()
    adapter = StackSpotAdapter(config)

    if not adapter.is_available():
        logger.error("❌ StackSpot not available. Check authentication.")
        return 1

    logger.info("✅ StackSpot authenticated")

    # 2. Get executor with tools
    logger.info("\n📋 Step 2: Creating StackSpotChain with tools")
    tools = [read_file, apply_diff]

    try:
        executor = adapter.get_model_with_tools(tools)
        logger.info(f"✅ Executor created: {type(executor).__name__}")
    except Exception as e:
        logger.error(f"❌ Error creating executor: {e}")
        return 1

    # 3. Prepare test input
    logger.info("\n📋 Step 3: Preparing test input")
    test_file = "buddyctl/integrations/langchain/examples/calculator.py"

    # Read file content
    with open(test_file, 'r') as f:
        file_lines = f.readlines()

    # Format with line numbers
    file_content_with_lines = "\n".join(
        f"{i+1:3} | {line.rstrip()}"
        for i, line in enumerate(file_lines)
    )

    user_input = f"""Add a comment to the add_two_numbers function explaining it adds two numbers.

File: {test_file} ({len(file_lines)} lines total)
────────────────────────────────────────────
{file_content_with_lines}
────────────────────────────────────────────"""

    logger.info(f"✅ Test input prepared (file: {test_file}, {len(file_lines)} lines)")

    # 4. Invoke chain
    logger.info("\n📋 Step 4: Invoking StackSpotChain")
    logger.info("Expected flow:")
    logger.info("  1. Call Main Agent → generate SEARCH/REPLACE blocks")
    logger.info("  2. Extract blocks")
    logger.info("  3. Local validation")
    logger.info("  4. Apply changes (or retry if validation fails)")
    logger.info("")

    try:
        result = executor.invoke(user_input)

        logger.info("\n" + "="*60)
        logger.info("✅ Chain execution completed!")
        logger.info("="*60)

        logger.info(f"\n📊 Results:")
        logger.info(f"  Output length: {len(result.get('output', ''))}")
        logger.info(f"  Tool calls made: {result.get('tool_calls_made', [])}")
        logger.info(f"  Validation rounds: {result.get('validation_rounds', 0)}")
        logger.info(f"  Blocks applied: {result.get('blocks_applied', 0)}")

        if result.get('error'):
            logger.error(f"  Error: {result['error']}")
            return 1

        logger.info("\n✅ Test completed successfully!")

        # Show what changed
        logger.info("\n📝 File modifications:")
        if result.get('blocks_applied', 0) > 0:
            logger.info(f"  {result['blocks_applied']} block(s) applied to {test_file}")
            logger.info("  Run 'git diff' to see changes")
        else:
            logger.info("  No modifications applied")

        return 0

    except Exception as e:
        logger.error(f"\n❌ Chain execution failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
