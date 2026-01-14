#!/bin/bash
# Start Book Server + ngrok tunnel for cloud workers

# Kill any existing processes
pkill -f "book_server" 2>/dev/null
pkill -f "ngrok" 2>/dev/null
sleep 1

cd /mnt/e/projects/bookcli

# Start book server in background
echo "Starting book server..."
nohup python3 book_server_v2.py > book_server.log 2>&1 &
SERVER_PID=$!
echo "Book server PID: $SERVER_PID"

sleep 2

# Start ngrok
echo "Starting ngrok tunnel..."
~/.local/bin/ngrok http 8765 --log=stdout &
NGROK_PID=$!
echo "Ngrok PID: $NGROK_PID"

sleep 5

# Get tunnel URL
TUNNEL_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'] if d['tunnels'] else '')" 2>/dev/null)

if [ -z "$TUNNEL_URL" ]; then
    echo "ERROR: Could not get ngrok URL"
    echo "Check: curl -s http://localhost:4040/api/tunnels"
else
    echo ""
    echo "=========================================="
    echo "📚 Book Server Ready!"
    echo "=========================================="
    echo ""
    echo "Tunnel URL: $TUNNEL_URL"
    echo ""
    echo "Use this URL in:"
    echo "  - Google Colab notebooks"
    echo "  - Kaggle notebooks"
    echo "  - HuggingFace Spaces"
    echo "  - GitHub Actions (cloud-workers.yml)"
    echo ""
    echo "Status: $TUNNEL_URL/status"
    echo ""
    echo "Press Ctrl+C to stop"
fi

# Wait for interrupt
wait $NGROK_PID
