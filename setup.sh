#!/usr/bin/env bash
# Run this once before starting the project:
#     bash setup.sh

set -e
echo "[1] Creating virtual environment..."
python3 -m venv .venv
echo "    Done."

echo ""
echo "[2] Activating virtual environment..."
source .venv/bin/activate
echo "    Done."
echo ""
echo "[3] Upgrading pip..."
pip install --upgrade pip -q
echo "    Done."

echo ""
echo "[4] Installing dependencies..."
pip install -r requirements.txt -q
echo "    Done."

echo ""
echo "[5] Training the ML model..."
python scripts/train_model.py
echo "    Done."

echo ""
echo "[6] Starting the app..."
echo "    Open http://127.0.0.1:5000 in your browser."
echo "    Press Ctrl+C to stop."
echo ""
FLASK_APP=app flask run
