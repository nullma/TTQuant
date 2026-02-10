#!/bin/bash

echo "=========================================="
echo "Clash Node Diagnostic Tool"
echo "=========================================="
echo ""

echo "[1] Testing proxy connection..."
curl -x http://127.0.0.1:7897 --connect-timeout 5 https://www.google.com -I 2>&1 | grep "HTTP" | head -1

echo ""
echo "[2] Checking IP location..."
IP_INFO=$(curl -x http://127.0.0.1:7897 --connect-timeout 5 -s https://ipapi.co/json/ 2>&1)
echo "$IP_INFO" | grep -E "ip|city|country_name|org" | head -10

echo ""
echo "[3] Testing Binance API..."
BINANCE_RESULT=$(curl -x http://127.0.0.1:7897 --connect-timeout 5 -s https://api.binance.com/api/v3/ping 2>&1)
if echo "$BINANCE_RESULT" | grep -q "restricted location"; then
    echo "❌ FAILED: Binance blocked (restricted location)"
    echo "   Current node is in a restricted region"
    echo ""
    echo "   Please switch to:"
    echo "   - 🇺🇸 US node"
    echo "   - 🇯🇵 Japan node"
    echo "   - 🇩🇪 Europe node"
elif echo "$BINANCE_RESULT" | grep -q "{}"; then
    echo "✅ SUCCESS: Binance API accessible"
else
    echo "⚠️  UNKNOWN: $BINANCE_RESULT"
fi

echo ""
echo "=========================================="
echo "Current Node Info:"
echo "=========================================="
echo "$IP_INFO" | python3 -m json.tool 2>/dev/null || echo "$IP_INFO"
echo ""
