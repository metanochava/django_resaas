from typing import Any

LABEL_KEYS = (
    "nome", "name", "title", "titulo",
    "descricao", "description", "label",
    "codigo", "code", "numero", "num",
    "username", "email"
)

def guess_name(obj: Any) -> str:
    """
    Retorna um label humano do objeto.
    Prioridade:
    1. nome / title / label
    2. outros campos comuns
    3. __str__
    4. id (fallback final)
    """

    if obj is None:
        return ""

    # ---------------- DICT ----------------
    if isinstance(obj, dict):
        for k in LABEL_KEYS:
            v = obj.get(k)
            if v not in (None, ""):
                return str(v)

        # tenta __str__ equivalente
        if obj:
            try:
                return str(obj)
            except:
                pass

        # fallback final → id
        return str(obj.get("id") or obj.get("pk") or "")

    # ---------------- OBJECT ----------------
    for k in LABEL_KEYS:
        if hasattr(obj, k):
            v = getattr(obj, k, None)
            if v not in (None, ""):
                return str(v)

    # ---------------- FULL NAME (User-like) ----------------
    if hasattr(obj, "get_full_name"):
        try:
            full = obj.get_full_name()
            if full:
                return str(full)
        except:
            pass

    if hasattr(obj, "first_name") and hasattr(obj, "last_name"):
        full = f"{getattr(obj, 'first_name', '')} {getattr(obj, 'last_name', '')}".strip()
        if full:
            return full

    # ---------------- __str__ ----------------
    try:
        s = str(obj)
        if s and s != object.__str__(obj):
            return s
    except:
        pass

    # ---------------- FINAL FALLBACK → ID ----------------
    if hasattr(obj, "id"):
        return str(getattr(obj, "id"))

    if hasattr(obj, "pk"):
        return str(getattr(obj, "pk"))

    return ""