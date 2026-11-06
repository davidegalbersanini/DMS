import os
import sys

# Se eseguito con --noconsole, stdout e stderr sono None su Windows.
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


def cleanup_old_instances():
    """Termina eventuali vecchie istanze rimaste in background e pulisce gli eseguibili temporanei."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        TH32CS_SNAPPROCESS = 0x00000002
        PROCESS_TERMINATE = 0x0001

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD),
                ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.c_size_t),
                ('th32ModuleID', wintypes.DWORD),
                ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD),
                ('pcPriClassBase', wintypes.LONG),
                ('dwFlags', wintypes.DWORD),
                ('szExeFile', ctypes.c_char * 260)
            ]

        kernel32 = ctypes.windll.kernel32
        my_pid = os.getpid()
        my_ppid = os.getppid()
        safe_pids = {my_pid, my_ppid}

        target_names = {
            "dms.exe",
            "dms_old.exe",
            "dms_old_run.exe",
            "dms_backup.exe",
            "dms_to_delete.exe"
        }

        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snap != -1:
            pe = PROCESSENTRY32()
            pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
            procs = []
            if kernel32.Process32First(snap, ctypes.byref(pe)):
                while True:
                    exe_name = pe.szExeFile.decode('utf-8', errors='ignore').lower()
                    procs.append((pe.th32ProcessID, pe.th32ParentProcessID, exe_name))
                    if not kernel32.Process32Next(snap, ctypes.byref(pe)):
                        break
            kernel32.CloseHandle(snap)

            # Proteggi anche il processo nonno se appartiene alla catena corrente
            for pid, ppid, _ in procs:
                if pid == my_ppid:
                    safe_pids.add(ppid)

            for pid, ppid, exe_name in procs:
                if exe_name in target_names and pid not in safe_pids:
                    h_proc = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
                    if h_proc:
                        kernel32.TerminateProcess(h_proc, 0)
                        kernel32.CloseHandle(h_proc)
    except Exception:
        pass

    time.sleep(0.2)
    exe_dir = get_exe_dir()
    for old_file in ["DMS_old_run.exe", "DMS_old.exe", "DMS_backup.exe", "DMS_to_delete.exe"]:
        p = os.path.join(exe_dir, old_file)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    # Importante su Windows: allow_reuse_address = False evita che due istanze facciano bind sulla stessa porta
    allow_reuse_address = False
    daemon_threads = True


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.15)
        return s.connect_ex(('127.0.0.1', port)) == 0


def find_bindable_server(start_port=8765):
    """Trova una porta realmente libera verificando che nessun altro processo sia in ascolto."""
    for p in range(start_port, start_port + 50):
        if is_port_in_use(p):
            continue
        try:
            httpd = ReusableThreadingTCPServer(('127.0.0.1', p), DMSRequestHandler)
            return httpd, p
        except OSError:
            continue
    httpd = ReusableThreadingTCPServer(('127.0.0.1', 0), DMSRequestHandler)
    actual_port = httpd.server_address[1]
    return httpd, actual_port


def launch_desktop_gui(url):
    """
    Apre l'interfaccia in modalità App Desktop richiedendo la finestra massimizzata.
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

        # Non passare --window-size insieme a --start-maximized altrimenti Chromium ignora --start-maximized
        flags = [
            f"--app={url}",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 3  # SW_MAXIMIZE

        for ep in edge_paths:
            if os.path.exists(ep):
                try:
                    subprocess.Popen([ep] + flags, startupinfo=si)
                    return
                except Exception:
                    pass

        for cp in chrome_paths:
            if os.path.exists(cp):
                try:
                    subprocess.Popen([cp] + flags, startupinfo=si)
                    return
                except Exception:
                    pass

    webbrowser.open(url)


def maximize_and_monitor_window(port):
    """
    Intercetta la finestra DMS tramite le API native di Windows (user32.dll),
    la forza a schermo intero massimizzato (SW_MAXIMIZE / SC_MAXIMIZE) e chiude
    automaticamente il server in background quando l'utente chiude la finestra.
    """
    if sys.platform != "win32":
        while True:
            time.sleep(1)
        return

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        SW_MAXIMIZE = 3
        WM_SYSCOMMAND = 0x0112
        SC_MAXIMIZE = 0xF030

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def find_dms_windows():
            found = []
            def enum_cb(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        title = buf.value
                        if "DMS - Developments Management System" in title or f"127.0.0.1:{port}" in title:
                            found.append(hwnd)
                return True
            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
            return found

        tracked_hwnd = None
        def set_window_icons(h):
            try:
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010

                icon_candidates = [
                    os.path.join(get_exe_dir(), "app_icon.ico"),
                    os.path.join(getattr(sys, '_MEIPASS', ''), "dms_app", "static", "favicon.ico"),
                    os.path.join(current_dir, "static", "favicon.ico")
                ]
                icon_file = None
                for c in icon_candidates:
                    if os.path.exists(c):
                        icon_file = c
                        break

                if icon_file:
                    h_big = user32.LoadImageW(0, icon_file, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
                    h_small = user32.LoadImageW(0, icon_file, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    if h_big:
                        user32.SendMessageW(h, WM_SETICON, ICON_BIG, h_big)
                    if h_small:
                        user32.SendMessageW(h, WM_SETICON, ICON_SMALL, h_small)
            except Exception:
                pass

        # Fase 1: Attendi la comparsa della finestra (fino a 15 secondi) e massimizzala subito
        start_wait = time.time()
        while time.time() - start_wait < 15.0:
            hwnds = find_dms_windows()
            if hwnds:
                tracked_hwnd = hwnds[0]
                for h in hwnds:
                    set_window_icons(h)
                    user32.ShowWindowAsync(h, SW_MAXIMIZE)
                    user32.ShowWindow(h, SW_MAXIMIZE)
                    user32.PostMessageW(h, WM_SYSCOMMAND, SC_MAXIMIZE, 0)
                    user32.SetForegroundWindow(h)
                break
            time.sleep(0.1)

        # Fase 2: Per i primi 2 secondi continua a forzare lo stato massimizzato
        # (nel caso in cui Edge tenti di ripristinare le dimensioni salvate nel profilo utente)
        if tracked_hwnd:
            enforce_until = time.time() + 2.0
            while time.time() < enforce_until:
                for h in find_dms_windows():
                    set_window_icons(h)
                    if not user32.IsZoomed(h) and not user32.IsIconic(h):
                        user32.ShowWindowAsync(h, SW_MAXIMIZE)
                        user32.ShowWindow(h, SW_MAXIMIZE)
                        user32.PostMessageW(h, WM_SYSCOMMAND, SC_MAXIMIZE, 0)
                time.sleep(0.15)

            # Fase 3: Rimani attivo finché la finestra DMS è aperta; chiudi il processo quando viene chiusa
            missing_ticks = 0
            while True:
                alive = user32.IsWindow(tracked_hwnd) or bool(find_dms_windows())
                if not alive:
                    missing_ticks += 1
                    if missing_ticks >= 3:
                        break
                else:
                    missing_ticks = 0
                time.sleep(0.5)
        else:
            # Fallback se non ha trovato l'handle della finestra
            while True:
                time.sleep(1)
    except Exception:
        while True:
            time.sleep(1)


def main():
    try:
        cleanup_old_instances()
        database.init_db()
        httpd, port = find_bindable_server(8765)
        url = f"http://127.0.0.1:{port}"

        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        time.sleep(0.3)
        launch_desktop_gui(url)
        maximize_and_monitor_window(port)
        os._exit(0)
    except Exception:
        try:
            log_file = os.path.join(get_exe_dir(), "dms_crash.log")
            with open(log_file, "w", encoding="utf-8") as f:
                import traceback
                f.write(traceback.format_exc())
        except Exception:
            pass


if __name__ == "__main__":
    main()
