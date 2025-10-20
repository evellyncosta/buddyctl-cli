"""Test with real Judge Agent response from logs."""

import re


def extract_json(text: str) -> str:
    """Extract JSON from markdown code blocks or plain text."""
    print("=" * 80)
    print("INPUT TEXT (first 1000 chars):")
    print("=" * 80)
    print(text[:1000])
    print()

    stripped = text.strip()

    # If text starts with { or [, it's raw JSON (no markdown blocks)
    if stripped.startswith('{') or stripped.startswith('['):
        print("✅ Text starts with { or [ - returning as raw JSON")
        print(f"Length: {len(stripped)}")
        return stripped

    # Try JSON markdown code blocks first (```json)
    match = re.search(r'```json\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        result = match.group(1).strip()
        print("✅ Found ```json block")
        print(f"Extracted length: {len(result)}")
        return result

    # If no ```json block, try plain ``` blocks
    match = re.search(r'```\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        result = match.group(1).strip()
        print("⚠️  Found plain ``` block (no json label)")
        print(f"Extracted length: {len(result)}")
        print(f"First 200 chars: {result[:200]}")
        return result

    # If no code blocks, return the whole text
    print("ℹ️  No code blocks found, returning full text")
    print(f"Full text length: {len(text)}")
    return stripped


# Real case from logs: Judge returns JSON without markdown blocks
real_judge_response = """{
  "needs_tools": true,
  "tool_calls": [
    {
      "name": "apply_diff",
      "args": {
        "diff_content": "--- a/test-cases/README.md\\n+++ b/test-cases/README.md\\n@@ -2,7 +2,7 @@\\n # README.md\\n \\n ## Overview\\n-This project uses Spring Boot with Gradle and relies on a local Docker Compose environment for PostgreSQL and LocalStack (S3).\\n+This project uses Spring Boot with Gradle and relies on a local Docker Compose environment for PostgreSQL, LocalStack (S3), and Kafka for event tracking.\\n \\n ---\\n \\n## Prerequisites\\n\\n- Docker and Docker Compose installed\\n- (Optional) AWS CLI installed for S3 testing\\n\\n---\\n\\n## 1. Configure GitHub Packages Credentials\\n\\n```bash\\ncp gradle.properties.example gradle.properties\\n```\\n\\n2. Edit with your GitHub credentials\\n\\n---\\n\\n## More content here\\n    - **postgres_local**: PostgreSQL available at `localhost:5433`\\n    - **localstack_s3**: Local S3 available at `localhost:4566`\\n+   - **kafka**: Apache Kafka available at `localhost:9092` for event tracking"
      }
    }
  ]
}"""

print("\n")
print("=" * 80)
print("TEST: Real Judge Agent Response")
print("=" * 80)
result = extract_json(real_judge_response)

print()
print("=" * 80)
print("RESULT:")
print("=" * 80)
print(f"Length: {len(result)}")
print(f"First 300 chars: {result[:300]}")

# Try to parse
import json
try:
    parsed = json.loads(result)
    print("\n✅ JSON parsed successfully!")
    print(f"needs_tools: {parsed.get('needs_tools')}")
except json.JSONDecodeError as e:
    print(f"\n❌ JSON parse failed: {e}")
