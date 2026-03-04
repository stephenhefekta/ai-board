import sys
import os
from pathlib import Path

# For PyInstaller bundles, resources live in sys._MEIPASS
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

# Load API keys from ~/ai-board/.env before importing app
from dotenv import load_dotenv
load_dotenv(Path.home() / 'ai-board' / '.env')

import socket
import threading
import time
import urllib.request
import uvicorn
import webview
from app import app as fastapi_app


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _run_server(port: int):
    uvicorn.run(fastapi_app, host='127.0.0.1', port=port, log_level='error')


def main():
    port = _free_port()
    threading.Thread(target=_run_server, args=(port,), daemon=True).start()

    # Wait up to ~4 s for server to accept connections
    url = f'http://127.0.0.1:{port}'
    for _ in range(30):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.15)

    webview.create_window('AI Board', url, width=1400, height=900, min_size=(800, 600))
    webview.start()


if __name__ == '__main__':
    main()
