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

"""
Example: Using LangChain to modify calculator from 2 numbers to 3 numbers.

This example demonstrates:
1. Using the Coder Agent to modify existing code
2. Using the Differ Agent to generate a git-style diff
3. Orchestrating multiple StackSpot agents with LangChain

Before running:
1. Set environment variables:
   export STACKSPOT_CLIENT_ID=your_client_id
   export STACKSPOT_CLIENT_SECRET=your_client_secret
   export STACKSPOT_REALM=your_realm

2. Set your agent IDs:
   export CODER_AGENT_ID=your-coder-agent-id
   export DIFFER_AGENT_ID=your-differ-agent-id
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from buddyctl.integrations.langchain import create_coder_differ_chain


def main():
    """Run the calculator modification example."""
    # Get agent IDs from environment
    coder_agent_id = os.getenv("STACKSPOT_CODER_ID")
    differ_agent_id = os.getenv("STACKSPOT_DIFFER_ID")

    if not coder_agent_id or not differ_agent_id:
        print("Error: Set CODER_AGENT_ID and DIFFER_AGENT_ID environment variables")
        sys.exit(1)

    # Get the path to the calculator file
    calculator_file = Path(__file__).parent / "calculator.py"

    if not calculator_file.exists():
        print(f"Error: Calculator file not found at {calculator_file}")
        sys.exit(1)

    # Create the chain
    chain = create_coder_differ_chain(
        coder_agent_id=coder_agent_id, differ_agent_id=differ_agent_id
    )

    # Define the modification instruction
    instruction = """
    Modify the function add_two_numbers to add_three_numbers that accepts three parameters (a, b, c).
    Update the function to sum all three numbers.
    Update the docstring accordingly.
    Update the test examples in __main__ to use three numbers.
    Keep the same license header and code style.
    """

    try:
        # Execute the chain
        result = chain.invoke(
            {"file_path": str(calculator_file), "instruction": instruction.strip()}
        )

        # Display results
        print("DIFF:")
        print(result["diff"])

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
