#!/usr/bin/env bash

echo "=================================="
echo " Smart Student Performance System"
echo "=================================="

echo ""
echo "Installing packages..."
echo ""

pip install flask==3.1.1 && echo "  flask done" || exit 1
pip install flask-sqlalchemy==3.1.1 && echo "  flask-sqlalchemy done" || exit 1
pip install werkzeug==3.1.3 && echo "  werkzeug done" || exit 1
pip install scikit-learn==1.6.1 && echo "  scikit-learn done" || exit 1
pip install pandas==2.2.3 && echo "  pandas done" || exit 1

echo ""
echo "Training the model..."
python scripts/train_model.py || exit 1

echo ""
echo "Starting the app at http://127.0.0.1:5000"
echo "Press Ctrl+C to stop."
echo ""
FLASK_APP=app flask run
