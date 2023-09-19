#! /bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
uvicorn main:app --uds=/tmp/uvicorn.sock