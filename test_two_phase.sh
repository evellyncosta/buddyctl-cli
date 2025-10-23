#!/bin/bash

# Test Two-Phase Pattern (Main Agent → Judge Agent) via curl
# POC to validate if the workflow works correctly before implementation

set -e

echo "=========================================="
echo "Two-Phase Pattern Test via curl"
echo "=========================================="
echo ""

# Configuration
MAIN_AGENT_ID="01K48VKDG5461HGS5D3QACWMBA"
JUDGE_AGENT_ID="01K48SKQWX4D7A3AYF0P02X6GK"
API_BASE_URL="https://genai-inference-app.stackspot.com"

# Get token from credentials
TOKEN=$(cat ~/.buddyctl/credentials.json | python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
    echo "❌ ERROR: Could not get access token"
    exit 1
fi

echo "✅ Token obtained (${TOKEN:0:20}...)"
echo ""

# Prepare file content with line numbers (format used by buddyctl)
FILE_CONTENT="File: buddyctl/integrations/langchain/examples/calculator.py (72 lines total)
────────────────────────────────────────────────────────────
 1 | # Copyright 2024 Evellyn
 2 | #
 3 | # Licensed under the Apache License, Version 2.0 (the \"License\");
 4 | # you may not use this file except in compliance with the License.
 5 | # You may obtain a copy of the License at
 6 | #
 7 | #     http://www.apache.org/licenses/LICENSE-2.0
 8 | #
 9 | # Unless required by applicable law or agreed to in writing, software
10 | # distributed under the License is distributed on an \"AS IS\" BASIS,
11 | # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
12 | # See the License for the specific language governing permissions and
13 | # limitations under the License.
14 |
15 | \"\"\"Simple calculator module.\"\"\"
16 |
17 |
18 | def add_two_numbers(a: float, b: float) -> float:
19 |     \"\"\"Add two numbers together.
20 |
21 |     Args:
22 |         a: First number
23 |         b: Second number
24 |
25 |     Returns:
26 |         Sum of a and b
27 |     \"\"\"
28 |     return a + b
29 |
30 |
31 | def subtract_two_numbers(a: float, b: float) -> float:
32 |     \"\"\"Subtract two numbers.
33 |
34 |     Args:
35 |         a: First number (minuend)
36 |         b: Second number (subtrahend)
37 |
38 |     Returns:
39 |         Subtraction of b from a
40 |     \"\"\"
41 |     return a - b
42 |
43 |
44 | def divide_two_numbers(a: float, b: float) -> float:
45 |     \"\"\"Divide two numbers.
46 |
47 |     Args:
48 |         a: First number (dividend)
49 |         b: Second number (divisor)
50 |
51 |     Returns:
52 |         Division of a by b
53 |     \"\"\"
54 |     return a / b
55 |
56 |
57 | if __name__ == \"__main__\":
58 |     # Test the function
59 |     result = add_two_numbers(10, 20)
60 |     print(f\"10 + 20 = {result}\")
61 |
62 |     result = add_two_numbers(5.5, 3.2)
63 |     print(f\"5.5 + 3.2 = {result}\")
64 |
65 |     result = divide_two_numbers(10, 20)
66 |     print(f\"10 / 20 = {result}\")
67 |
68 |     result = divide_two_numbers(5.5, 3.2)
69 |     print(f\"5.5 / 3.2 = {result}\")
70 |
71 |     result = subtract_two_numbers(10, 3)
72 |     print(f\"10 - 3 = {result}\")
────────────────────────────────────────────────────────────"

# User request with file context
USER_REQUEST="Add a multiply function to the calculator.

$FILE_CONTENT"

echo "📤 Step 1: Calling Main Agent..."
echo "   Agent ID: $MAIN_AGENT_ID"
echo "   Request: Add multiply function"
echo ""

# Call Main Agent
MAIN_RESPONSE=$(curl -s -X POST "$API_BASE_URL/v1/agent/$MAIN_AGENT_ID/chat" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"streaming\": false,
        \"user_prompt\": $(echo "$USER_REQUEST" | jq -Rs .),
        \"stackspot_knowledge\": false,
        \"return_ks_in_response\": true
    }")

# Check if Main Agent call was successful
if echo "$MAIN_RESPONSE" | jq -e '.message' > /dev/null 2>&1; then
    MAIN_MESSAGE=$(echo "$MAIN_RESPONSE" | jq -r '.message')
    echo "✅ Main Agent responded"
    echo ""
    echo "────────────────────────────────────────────────────────────"
    echo "Main Agent Response (first 500 chars):"
    echo "────────────────────────────────────────────────────────────"
    echo "${MAIN_MESSAGE:0:500}..."
    echo "────────────────────────────────────────────────────────────"
    echo ""

    # Save full response to file
    echo "$MAIN_MESSAGE" > /tmp/main_agent_response.txt
    echo "💾 Full Main Agent response saved to: /tmp/main_agent_response.txt"
    echo ""
else
    echo "❌ ERROR: Main Agent call failed"
    echo "$MAIN_RESPONSE" | jq '.'
    exit 1
fi

echo "📤 Step 2: Calling Judge Agent..."
echo "   Agent ID: $JUDGE_AGENT_ID"
echo "   Task: Analyze Main Agent response and validate diff"
echo ""

# Prepare Judge Agent input (following the prompt format in prompts/judge_agent.md)
JUDGE_INPUT="{
  \"diff\": \"extract_from_main_response\",
  \"original_file\": \"buddyctl/integrations/langchain/examples/calculator.py\",
  \"modification_type\": \"add_function\",
  \"main_agent_response\": $(echo "$MAIN_MESSAGE" | jq -Rs .)
}"

# Call Judge Agent
JUDGE_RESPONSE=$(curl -s -X POST "$API_BASE_URL/v1/agent/$JUDGE_AGENT_ID/chat" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"streaming\": false,
        \"user_prompt\": $(echo "$JUDGE_INPUT" | jq -Rs .),
        \"stackspot_knowledge\": false,
        \"return_ks_in_response\": true
    }")

# Check if Judge Agent call was successful
if echo "$JUDGE_RESPONSE" | jq -e '.message' > /dev/null 2>&1; then
    JUDGE_MESSAGE=$(echo "$JUDGE_RESPONSE" | jq -r '.message')
    echo "✅ Judge Agent responded"
    echo ""
    echo "────────────────────────────────────────────────────────────"
    echo "Judge Agent Response:"
    echo "────────────────────────────────────────────────────────────"
    echo "$JUDGE_MESSAGE" | jq '.' 2>/dev/null || echo "$JUDGE_MESSAGE"
    echo "────────────────────────────────────────────────────────────"
    echo ""

    # Save full response to file
    echo "$JUDGE_MESSAGE" > /tmp/judge_agent_response.txt
    echo "💾 Full Judge Agent response saved to: /tmp/judge_agent_response.txt"
    echo ""
else
    echo "❌ ERROR: Judge Agent call failed"
    echo "$JUDGE_RESPONSE" | jq '.'
    exit 1
fi

echo "=========================================="
echo "✅ Two-Phase Test Complete!"
echo "=========================================="
echo ""
echo "📁 Output files:"
echo "   - /tmp/main_agent_response.txt (Main Agent full response)"
echo "   - /tmp/judge_agent_response.txt (Judge Agent validation result)"
echo ""
echo "🔍 Next Steps:"
echo "   1. Review Main Agent response - does it contain a valid diff?"
echo "   2. Review Judge Agent response - did it call the validation API?"
echo "   3. Check validation_status: valid/invalid/error"
echo "   4. Check recommendation: proceed/regenerate/abort"
echo ""
