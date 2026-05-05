#!/bin/bash

echo "🔐 Testing Zyra Security Shield (PII Masking)..."
echo "-----------------------------------------------"

# 1. Test Email Masking
echo "Test 1: Email Masking"
curl -s -X POST http://127.0.0.1:8081/v1/chat \
     -H "Content-Type: application/json" \
     -d '{"text": "My email is secret@zyrabit.com, please dont share it.", "client_msg_id": "sec-test-1"}' | jq .metadata
echo -e "\n"

# 2. Test IP Masking
echo "Test 2: IP Masking"
curl -s -X POST http://127.0.0.1:8081/v1/chat \
     -H "Content-Type: application/json" \
     -d '{"text": "Connect to the database at 192.168.1.100", "client_msg_id": "sec-test-2"}' | jq .metadata
echo -e "\n"

# 3. Test Credit Card Masking
echo "Test 3: Credit Card Masking"
curl -s -X POST http://127.0.0.1:8081/v1/chat \
     -H "Content-Type: application/json" \
     -d '{"text": "Charge it to 4532 1234 5678 9012 please.", "client_msg_id": "sec-test-3"}' | jq .metadata
echo -e "\n"

echo "🏁 Security Tests Sent. Check your uvicorn logs for [PII Detected] messages."
