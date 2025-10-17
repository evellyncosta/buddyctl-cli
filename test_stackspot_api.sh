#!/bin/bash

# Test StackSpot API directly with curl to validate stability

set -e

echo "=========================================="
echo "StackSpot API Direct Test"
echo "=========================================="
echo ""

# Load environment variables
source ~/.bashrc 2>/dev/null || true

# Check credentials
if [ -z "$STACKSPOT_CLIENT_ID" ] || [ -z "$STACKSPOT_CLIENT_SECRET" ] || [ -z "$STACKSPOT_REALM" ]; then
    echo "❌ Error: StackSpot credentials not found in environment"
    echo "Please set: STACKSPOT_CLIENT_ID, STACKSPOT_CLIENT_SECRET, STACKSPOT_REALM"
    exit 1
fi

AGENT_ID="01K48SKQWX4D7A3AYF0P02X6GJ"
API_BASE="https://genai-inference-app.stackspot.com"

echo "1. Authenticating with StackSpot..."
echo "   Realm: $STACKSPOT_REALM"

# Get access token
AUTH_RESPONSE=$(curl -s -X POST "https://idm.stackspot.com/$STACKSPOT_REALM/oidc/oauth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$STACKSPOT_CLIENT_ID" \
    -d "client_secret=$STACKSPOT_CLIENT_SECRET" \
    -d "grant_type=client_credentials")

ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Failed to get access token"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo "✅ Authenticated successfully"
echo "   Token: ${ACCESS_TOKEN:0:20}..."
echo ""

# Test 1: Non-streaming request
echo "=========================================="
echo "Test 1: Non-Streaming Request"
echo "=========================================="
echo ""

echo "Making POST to: $API_BASE/v1/agent/$AGENT_ID/chat"
echo "Payload: streaming=false"
echo ""

NON_STREAM_START=$(date +%s)

NON_STREAM_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME_TOTAL:%{time_total}" \
    -X POST "$API_BASE/v1/agent/$AGENT_ID/chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "streaming": false,
        "user_prompt": "Responda apenas: OK",
        "stackspot_knowledge": false,
        "return_ks_in_response": true
    }')

NON_STREAM_END=$(date +%s)
NON_STREAM_DURATION=$((NON_STREAM_END - NON_STREAM_START))

HTTP_CODE=$(echo "$NON_STREAM_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
TIME_TOTAL=$(echo "$NON_STREAM_RESPONSE" | grep "TIME_TOTAL:" | cut -d: -f2)
RESPONSE_BODY=$(echo "$NON_STREAM_RESPONSE" | sed '/HTTP_CODE:/,$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo ""
echo "Status: HTTP $HTTP_CODE"
echo "Duration: ${TIME_TOTAL}s (wall clock: ${NON_STREAM_DURATION}s)"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Non-streaming request successful"
else
    echo "❌ Non-streaming request failed"
fi

echo ""

# Test 2: Streaming request
echo "=========================================="
echo "Test 2: Streaming Request (SSE)"
echo "=========================================="
echo ""

echo "Making POST to: $API_BASE/v1/agent/$AGENT_ID/chat"
echo "Payload: streaming=true"
echo ""

STREAM_START=$(date +%s)

echo "Streaming response:"
echo "---"

timeout 30 curl -N -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "$API_BASE/v1/agent/$AGENT_ID/chat" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: text/event-stream" \
    -H "Cache-Control: no-cache" \
    -d '{
        "streaming": true,
        "user_prompt": "Responda apenas: OK",
        "stackspot_knowledge": false,
        "return_ks_in_response": true
    }' 2>&1

STREAM_EXIT_CODE=$?
STREAM_END=$(date +%s)
STREAM_DURATION=$((STREAM_END - STREAM_START))

echo "---"
echo ""
echo "Duration: ${STREAM_DURATION}s"

if [ $STREAM_EXIT_CODE -eq 0 ]; then
    echo "✅ Streaming request completed"
elif [ $STREAM_EXIT_CODE -eq 124 ]; then
    echo "❌ Streaming request timed out (30s)"
else
    echo "❌ Streaming request failed (exit code: $STREAM_EXIT_CODE)"
fi

echo ""

# Test 3: Multiple sequential streaming requests (simulate ReAct)
echo "=========================================="
echo "Test 3: Multiple Sequential Streaming Requests"
echo "=========================================="
echo "Simulating ReAct Agent with 3 sequential calls"
echo ""

MULTI_SUCCESS=0
MULTI_FAILED=0

for i in {1..3}; do
    echo "Call $i/3:"

    CALL_START=$(date +%s)

    CALL_RESPONSE=$(timeout 30 curl -N -s -w "\nEXIT_CODE:$?" \
        -X POST "$API_BASE/v1/agent/$AGENT_ID/chat" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -H "Accept: text/event-stream" \
        -H "Cache-Control: no-cache" \
        -d "{
            \"streaming\": true,
            \"user_prompt\": \"Responda apenas: OK $i\",
            \"stackspot_knowledge\": false,
            \"return_ks_in_response\": true
        }" 2>&1)

    CALL_EXIT=$?
    CALL_END=$(date +%s)
    CALL_DURATION=$((CALL_END - CALL_START))

    if [ $CALL_EXIT -eq 0 ]; then
        echo "  ✅ Success (${CALL_DURATION}s)"
        MULTI_SUCCESS=$((MULTI_SUCCESS + 1))
    elif [ $CALL_EXIT -eq 124 ]; then
        echo "  ❌ Timeout (${CALL_DURATION}s)"
        MULTI_FAILED=$((MULTI_FAILED + 1))
    else
        echo "  ❌ Failed - exit code $CALL_EXIT (${CALL_DURATION}s)"
        MULTI_FAILED=$((MULTI_FAILED + 1))
    fi

    # Small delay between calls
    sleep 0.5
done

echo ""
echo "Results: $MULTI_SUCCESS successful, $MULTI_FAILED failed"
echo ""

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "Test 1 (Non-streaming): $([ "$HTTP_CODE" = "200" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "Test 2 (Streaming):     $([ $STREAM_EXIT_CODE -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "Test 3 (Multi-stream):  $MULTI_SUCCESS/3 successful"
echo ""

if [ $MULTI_FAILED -gt 0 ]; then
    echo "⚠️  CONCLUSION: StackSpot API has stability issues with streaming"
    echo "   Recommendation: Use non-streaming or implement robust retry logic"
else
    echo "✅ CONCLUSION: StackSpot API is stable"
    echo "   The issue may be in the client implementation"
fi

echo ""
