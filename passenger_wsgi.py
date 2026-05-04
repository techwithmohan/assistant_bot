import sys
import os

# 1. Add the current directory to the Python path
INTERP = os.path.expanduser("~/virtualenv/python_app/3.10/bin/python")
if sys.executable != INTERP: os.execl(INTERP, INTERP, *sys.argv)
sys.path.insert(0, os.path.dirname(__file__))

# 2. Import the Flask app from our bot_webhook file
from bot_webhook import flask_app as application
