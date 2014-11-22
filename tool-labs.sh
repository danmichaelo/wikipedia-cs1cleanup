#!/bin/sh

echo "=== This is DanmicholoBot running on $(hostname) ==="

. ENV/bin/activate
python run.py

