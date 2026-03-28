#!/usr/bin/env bash
# exit on error
set -e

echo "Installing requirements..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate

echo "Build successful!"
