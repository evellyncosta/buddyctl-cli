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

"""Example: Coder → Differ chain using StackSpot agents.

This example demonstrates how to use the LangChain integration to orchestrate
two StackSpot agents:
1. Coder Agent: Generates/modifies code based on instructions
2. Differ Agent: Produces git-style diff of the changes

Requirements:
    - Environment variables set in .env file:
        * STACKSPOT_CLIENT_ID
        * STACKSPOT_CLIENT_SECRET
        * STACKSPOT_REALM
        * CODER_AGENT_ID (optional, defaults to placeholder)
        * DIFFER_AGENT_ID (optional, defaults to placeholder)
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import buddyctl
sys.path.insert(0, str(Path(__file__).parent.parent))

from buddyctl.langchain_integration import create_coder_differ_chain


def create_example_file() -> str:
    """Create an example Python file to be modified.
    
    Returns:
        Path to the created file
    """
    example_code = '''def register_user(name, email):
    """Register a new user in the system."""
    user = User(name=name, email=email)
    user.save()
    return user


def calculate_total(items):
    """Calculate total price of items."""
    total = 0
    for i in range(len(items)):
        total = total + items[i].price
    return total
'''
    
    file_path = "example_code.py"
    Path(file_path).write_text(example_code)
    return file_path


def print_section(title: str, content: str = None):
    """Print a formatted section."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)
    if content:
        print(content)


def main():
    """Run the Coder → Differ chain example."""
    
    print_section("🤖 StackSpot Coder → Differ Chain - MVP Demo")
    
    # Check environment variables
    required_vars = [
        "STACKSPOT_CLIENT_ID",
        "STACKSPOT_CLIENT_SECRET",
        "STACKSPOT_REALM"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"\n❌ Missing environment variables: {', '.join(missing)}")
        print("Please set them in your .env file")
        print("\nExample .env file:")
        print("STACKSPOT_CLIENT_ID=your_client_id")
        print("STACKSPOT_CLIENT_SECRET=your_client_secret")
        print("STACKSPOT_REALM=your_realm")
        print("CODER_AGENT_ID=your-coder-agent-id")
        print("DIFFER_AGENT_ID=your-differ-agent-id")
        return 1
    
    # Get agent IDs (use environment variables or placeholders)
    coder_agent_id = os.getenv("CODER_AGENT_ID", "your-coder-agent-id")
    differ_agent_id = os.getenv("DIFFER_AGENT_ID", "your-differ-agent-id")
    
    if coder_agent_id == "your-coder-agent-id":
        print("\n⚠️  Using placeholder agent IDs!")
        print("Set CODER_AGENT_ID and DIFFER_AGENT_ID in your .env file")
        print("This example will fail without real agent IDs\n")
    
    # Create example file
    print_section("📝 Step 1: Creating Example File")
    example_file = create_example_file()
    original_code = Path(example_file).read_text()
    print(f"Created: {example_file}")
    print(f"\n{original_code}")
    
    # Create the chain
    print_section("🔗 Step 2: Creating Coder → Differ Chain")
    print(f"Coder Agent ID: {coder_agent_id}")
    print(f"Differ Agent ID: {differ_agent_id}")
    
    try:
        chain = create_coder_differ_chain(
            coder_agent_id=coder_agent_id,
            differ_agent_id=differ_agent_id
        )
        print("✅ Chain created successfully!")
    except Exception as e:
        print(f"❌ Failed to create chain: {e}")
        return 1
    
    # Define instruction
    instruction = "Add email validation (must contain @) in register_user function"
    
    print_section("📋 Step 3: Instruction for Modification")
    print(instruction)
    
    # Execute the chain
    print_section("⚙️  Step 4: Executing Chain")
    print("This will:")
    print("  1. Read the original code")
    print("  2. Send to Coder Agent for modification")
    print("  3. Send original + modified to Differ Agent")
    print("  4. Generate git-style diff")
    print("\n⏳ Processing... (this may take 10-30 seconds)")
    
    try:
        result = chain.invoke({
            "file_path": example_file,
            "instruction": instruction
        })
        
        print("\n✅ Chain execution completed!")
        
    except Exception as e:
        print(f"\n❌ Chain execution failed: {e}")
        print("\nPossible causes:")
        print("  - Invalid agent IDs")
        print("  - Authentication issues (check .env credentials)")
        print("  - Network connectivity problems")
        print("  - StackSpot API errors")
        return 1
    
    # Display results
    print_section("📊 Step 5: Results")
    
    print("\n🔹 Original Code:")
    print("-" * 70)
    print(result["original_code"])
    
    print("\n🔹 Modified Code (from Coder Agent):")
    print("-" * 70)
    print(result["modified_code"])
    
    print("\n🔹 Diff (from Differ Agent):")
    print("-" * 70)
    print(result["diff"])
    
    print_section("✅ Demo Completed Successfully!")
    print("\nWhat happened:")
    print("  1. ✅ Read example_code.py")
    print("  2. ✅ Coder Agent generated modified code with validation")
    print("  3. ✅ Differ Agent produced git-style diff")
    print(f"  4. ✅ Total workflow completed")
    
    print("\n💡 Next Steps:")
    print("  - Apply the diff: git apply <diff-file>")
    print("  - Try different instructions")
    print("  - Integrate into your CLI with 'buddyctl code-diff'")
    print("  - Add more tools (write_file, apply_diff, etc)")
    
    # Cleanup
    if Path(example_file).exists():
        Path(example_file).unlink()
        print(f"\n🧹 Cleaned up: {example_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())