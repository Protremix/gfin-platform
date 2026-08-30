#!/bin/bash
set -e

echo "🛡️  Starting GFIN Security Scanner..."
echo ""

# Run the Python scanner
python3 /action/gfin_scan.py
