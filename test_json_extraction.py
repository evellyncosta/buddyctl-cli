"""Test JSON extraction from Judge Agent responses."""

import re


def extract_json(text: str) -> str:
    """
    Extract JSON from markdown code blocks or plain text.

    This is the same logic used in StackSpotChain._extract_json()
    """
    # Try JSON markdown code blocks first (```json)
    match = re.search(r'```json\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no ```json block, try plain ``` blocks
    match = re.search(r'```\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no code blocks, return the whole text
    return text.strip()


# Test Case 1: JSON com bloco ```json
test1 = """```json
{
  "needs_tools": true,
  "tool_calls": [
    {
      "name": "apply_diff",
      "args": {
        "diff_content": "--- a/file.py\\n+++ b/file.py\\n@@ -1,3 +1,3 @@"
      }
    }
  ]
}
```"""

print("=" * 80)
print("Test 1: JSON in ```json block")
print("=" * 80)
result1 = extract_json(test1)
print(f"Extracted ({len(result1)} chars):")
print(result1[:200])
print()

# Test Case 2: JSON com múltiplos blocos (JSON + DIFF)
test2 = """Here's the diff:

```diff
--- a/test-cases/README.md
+++ b/test-cases/README.md
@@ -2,7 +2,7 @@
 # README.md

 ## Overview
-This project uses Spring Boot
+This project uses Spring Boot and Kafka
```

And here's the tool call:

```json
{
  "needs_tools": true,
  "tool_calls": [
    {
      "name": "apply_diff",
      "args": {
        "diff_content": "--- a/file.py\\n+++ b/file.py"
      }
    }
  ]
}
```"""

print("=" * 80)
print("Test 2: Multiple blocks (diff + json)")
print("=" * 80)
result2 = extract_json(test2)
print(f"Extracted ({len(result2)} chars):")
print(result2[:200])
print()

# Test Case 3: JSON sem label explícito
test3 = """```
{
  "needs_tools": true,
  "tool_calls": []
}
```"""

print("=" * 80)
print("Test 3: JSON in plain ``` block")
print("=" * 80)
result3 = extract_json(test3)
print(f"Extracted ({len(result3)} chars):")
print(result3[:200])
print()

# Test Case 4: Resposta real do Judge Agent (do log)
test4 = """{
  "needs_tools": true,
  "tool_calls": [
    {
      "name": "apply_diff",
      "args": {
        "diff_content": "--- a/test-cases/README.md\\n+++ b/test-cases/README.md\\n@@ -2,7 +2,7 @@\\n # README.md\\n \\n ## Overview\\n-This project uses Spring Boot with Gradle and relies on a local Docker Compose environment for PostgreSQL and LocalStack (S3).\\n+This project uses Spring Boot with Gradle and relies on a local Docker Compose environment for PostgreSQL, LocalStack (S3), and Kafka for event tracking.\\n \\n ---\\n \\n ## Prerequisites"
      }
    }
  ]
}"""

print("=" * 80)
print("Test 4: Raw JSON (no code blocks)")
print("=" * 80)
result4 = extract_json(test4)
print(f"Extracted ({len(result4)} chars):")
print(result4[:200])
print()

# Test Case 5: Judge response com contexto (like the log shows)
test5 = """I'll analyze this and provide the tool call.

```json
{
  "needs_tools": true,
  "tool_calls": [
    {
      "name": "apply_diff",
      "args": {
        "diff_content": "--- a/test.py\\n+++ b/test.py\\n@@ -1,1 +1,1 @@\\n-# old\\n+# new"
      }
    }
  ]
}
```

This will apply the changes."""

print("=" * 80)
print("Test 5: JSON with context text")
print("=" * 80)
result5 = extract_json(test5)
print(f"Extracted ({len(result5)} chars):")
print(result5[:200])
print()

# Test parsing
print("=" * 80)
print("Testing JSON parsing")
print("=" * 80)

import json

for i, result in enumerate([result1, result2, result3, result4, result5], 1):
    try:
        parsed = json.loads(result)
        print(f"✅ Test {i}: Parsed successfully")
        print(f"   needs_tools: {parsed.get('needs_tools')}")
    except json.JSONDecodeError as e:
        print(f"❌ Test {i}: Parse failed - {e}")
    print()
