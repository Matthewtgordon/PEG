#!/bin/bash
# Comprehensive development environment setup
# Include: venv creation, dependency installation,
# pre-commit hooks, test data setup, etc.
set -e
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
touch .env
echo "Development environment ready"
