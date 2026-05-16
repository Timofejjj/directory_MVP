#!/bin/bash
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
python3 -c "from app import init_db; init_db()"
python3 app.py
