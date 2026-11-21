"""The paper formats a printable document may be produced on.

A thermal roll has a width and no fixed height: the page is as long as its
content (render.py measures it). The sheets have both."""

PAPER_FORMATS = {
    "thermal_58": {"label": "Thermal 58 mm", "width": 58, "height": None, "margin": 2, "thermal": True},
    "thermal_80": {"label": "Thermal 80 mm", "width": 80, "height": None, "margin": 3, "thermal": True},
    "a4": {"label": "A4", "width": 210, "height": 297, "margin": 12, "thermal": False},
    "a5": {"label": "A5", "width": 148, "height": 210, "margin": 10, "thermal": False},
    "a6": {"label": "A6", "width": 105, "height": 148, "margin": 7, "thermal": False},
    # half an A6 sheet (a slip: vital signs, a queue ticket...)
    "a7": {"label": "A7 (half A6)", "width": 74, "height": 105, "margin": 4, "thermal": False},
}

PAPER_CHOICES = tuple((code, paper["label"]) for code, paper in PAPER_FORMATS.items())


def paper(code):
    return PAPER_FORMATS.get(code)
