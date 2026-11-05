import json
import os
import sys

CONFIG_FILE_NAME = "dms_config.json"

def get_exe_dir():
    """Restituisce la cartella fisica in cui risiede l'eseguibile o lo script principale."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

get_app_dir = get_exe_dir

def get_bundle_dir():
    """Restituisce la cartella interna dove PyInstaller decomprime i file statici o la cartella corrente."""
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        if os.path.exists(os.path.join(base_path, "static")):
            return base_path
        # Fallback cartella exe
        exe_dir = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(exe_dir, "static")):
            return exe_dir
        if os.path.exists(os.path.join(exe_dir, "dms_app", "static")):
            return os.path.join(exe_dir, "dms_app")
        return base_path
    return os.path.dirname(os.path.abspath(__file__))

def get_config_path():
    return os.path.join(get_exe_dir(), CONFIG_FILE_NAME)

def load_config():
    """Carica la configurazione del percorso dati."""
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            pass
    
    # Cartella di default (cartella locale 'dms_shared_data' accanto all'eseguibile)
    default_data_dir = os.path.join(get_exe_dir(), "dms_shared_data")
    return {
        "shared_data_dir": default_data_dir,
        "is_configured": False
    }

def save_config(shared_data_dir):
    """Salva il percorso della cartella condivisa di rete."""
    config_path = get_config_path()
    os.makedirs(shared_data_dir, exist_ok=True)
    files_dir = os.path.join(shared_data_dir, "FILES")
    os.makedirs(files_dir, exist_ok=True)
    
    config_data = {
        "shared_data_dir": os.path.abspath(shared_data_dir),
        "is_configured": True
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
    return config_data

def get_db_path():
    cfg = load_config()
    data_dir = cfg.get("shared_data_dir")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "dms_database.db")

def get_files_dir():
    cfg = load_config()
    data_dir = cfg.get("shared_data_dir")
    files_dir = os.path.join(data_dir, "FILES")
    os.makedirs(files_dir, exist_ok=True)
    return files_dir
