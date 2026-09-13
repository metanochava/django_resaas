"""Interactive image picker for bootstrap commands (create_root.py,
create_entity.py) - requires a real logo/icon file when a new
Entity/EntityType is created, and never lets that be skipped.

Prefers a native OS file-picker dialog (tkinter), since these are
one-time interactive commands typically run by an admin at a
workstation. Bootstrap commands are also commonly run over SSH on a
headless server with no display though, so a missing tkinter/DISPLAY
falls back to typing the path in the terminal (same retry-until-valid
loop already used by create_root.py for username/password) instead of
crashing the whole command.
"""
import os

from PIL import Image, UnidentifiedImageError

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')


def _validate_image_path(path):
    if not path:
        return None, "No file selected."

    path = path.strip().strip('"').strip("'")

    if not os.path.isfile(path):
        return None, f"File not found: {path}"

    if not path.lower().endswith(IMAGE_EXTENSIONS):
        return None, f"Not a supported image type ({', '.join(IMAGE_EXTENSIONS)})."

    try:
        with Image.open(path) as img:
            img.verify()
    except (UnidentifiedImageError, OSError):
        return None, f"File is not a valid image: {path}"

    return path, None


def _pick_via_dialog(title):
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return filedialog.askopenfilename(
            title=title,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.webp *.bmp")],
        )
    finally:
        root.destroy()


def _warn(message, stdout=None, style=None):
    if stdout and style:
        stdout.write(style.WARNING(message))
    else:
        print(message)


def _pick_via_terminal(title, stdout=None, style=None):
    while True:
        path = input(f"{title} (full file path): ").strip()
        valid_path, error = _validate_image_path(path)
        if valid_path:
            return valid_path
        _warn(f"⚠ {error} Please try again.", stdout, style)


def pick_image_file(title="Select an image", stdout=None, style=None):
    """Blocks until a valid image file path is returned - there is no
    "skip"/empty outcome, callers must not treat this as optional."""
    try:
        while True:
            path = _pick_via_dialog(title)
            valid_path, error = _validate_image_path(path)
            if valid_path:
                return valid_path
            _warn(f"⚠ {error or 'No file selected.'} Please choose an image file.", stdout, style)
    except Exception:
        _warn("⚠ No graphical file dialog available — please type the file path instead.", stdout, style)
        return _pick_via_terminal(title, stdout=stdout, style=style)
