import os
import sys

# Se eseguito con --noconsole, stdout e stderr sono None su Windows.
# Reindirizziamo per prevenire eccezioni.
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, 'w')
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, 'w')
    except Exception:
        pass

import time
import socket
import threading
import subprocess
import webbrowser
import http.server
import socketserver

# Aggiungiamo la cartella al path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config import get_exe_dir, load_config
import database
from server import DMSRequestHandler

class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

def find_bindable_server(start_port=8765):
    """Trova una porta libera tentando l'effettivo bind del socket."""
    for p in range(start_port, start_port + 50):
        try:
            httpd = ReusableThreadingTCPServer(('127.0.0.1', p), DMSRequestHandler)
            return httpd, p
        except OSError:
            continue
    # Fallback su porta 0 (lascia scegliere all'OS)
    httpd = ReusableThreadingTCPServer(('127.0.0.1', 0), DMSRequestHandler)
    actual_port = httpd.server_address[1]
    return httpd, actual_port

def launch_desktop_gui(url):
    """
    Apre l'interfaccia in modalità 'App Desktop Standalone' tramite Microsoft Edge o Chrome,
    fornendo una vera e propria finestra applicativa senza barre del browser.
    Se non trovati, apre il browser predefinito di sistema.
    """
    if sys.platform == "win32":
        edge_paths = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe")
        ]
        chrome_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
        ]

        # Tentativo con Edge (preinstallato su ogni Windows 10/11)
        for ep in edge_paths:
            if os.path.exists(ep):
                try:
                    subprocess.Popen([ep, f"--app={url}", "--window-size=1400,900"])
                    return
                except Exception:
                    pass

        # Tentativo con Chrome
        for cp in chrome_paths:
            if os.path.exists(cp):
                try:
                    subprocess.Popen([cp, f"--app={url}", "--window-size=1400,900"])
                    return
                except Exception:
                    pass

    # Fallback browser standard
    webbrowser.open(url)

def main():
    try:
        database.init_db()
        httpd, port = find_bindable_server(8765)
        url = f"http://127.0.0.1:{port}"

        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        time.sleep(0.5)
        launch_desktop_gui(url)

        # Mantiene attivo il processo finché l'utente non lo chiude
        while True:
            time.sleep(1)
    except Exception as e:
        try:
            log_file = os.path.join(get_exe_dir(), "dms_crash.log")
            with open(log_file, "w", encoding="utf-8") as f:
                import traceback
                f.write(traceback.format_exc())
        except Exception:
            pass

if __name__ == "__main__":
    main()
