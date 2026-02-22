#!/bin/bash
cd "$(dirname "$0")"
pip install flask --break-system-packages -q
python app.py
