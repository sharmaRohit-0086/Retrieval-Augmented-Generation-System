#!/bin/bash

# Testing file upload
echo "Testing file upload..."
curl -X 'POST' \
'http://localhost:8000/uploadfile/' \
-H 'accept: application/json' \
-H 'Content-Type: multipart/form-data' \
-F 'file=@/usercode/obama.txt;type=text/plain'
echo ""
echo ""

# Testing the root endpoint
echo "Testing the root endpoint..."
curl -X 'GET' 'http://localhost:8000/' -H 'accept: application/json'
echo ""
echo ""

# Wait for 30 seconds before testing question answering
echo "Waiting for 30 seconds before testing question answering..."
sleep 30

# Testing question answering
echo "Testing question answering..."
curl -X 'POST' \
'http://localhost:8000/ask/' \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{"document_id": 1, "question": "When was Barack Obama elected for the second time ?"}'
echo ""
echo ""

# Testing similar chunk retrieval
echo "Testing similar chunk retrieval..."
curl -X 'POST' \
'http://localhost:8000/find-similar-chunks/1' \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{"question": "Who is Barack Obama wife and when did they meet ?"}'
echo ""
echo ""