
def find_settings_with_my_apps():
    """
    Procura automaticamente o settings.py que contém MY_APPS
    Funciona para qualquer estrutura:
      src/dev/settings.py
      config/settings.py
      project/settings.py
    """

    for path in Path.cwd().rglob("settings.py"):
        
        try:
            text = path.read_text()
            if "MY_APPS" in text:
                return path

        except Exception:
            continue

    return None
