import os
import tempfile

def safe_write(path, content, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    encoding = None if "b" in mode else "utf-8"

    if "a" in mode and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read() + content

    with tempfile.NamedTemporaryFile(
        delete=False,
        dir=os.path.dirname(path),
        mode="w" if "b" not in mode else "wb",
        encoding=encoding
    ) as tmp:
        tmp.write(content)
        temp_name = tmp.name

    os.replace(temp_name, path)
