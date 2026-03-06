import re


def clean_class_name(s: str):
    s = re.sub(r"[^a-zA-Z0-9_ ]", "", s)
    parts = re.split(r"[_\s]+", s)
    return "".join(p.capitalize() for p in parts if p)


def clean_file_name(s: str):
    # substitui espaços por _
    s = s.replace(" ", "_")

    # remove caracteres inválidos (mantém letras, números e _)
    s = re.sub(r"[^a-zA-Z0-9_]", "", s)

    # CamelCase → snake_case
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)

    return s.lower()


def clean_name(name: str) -> str:
    # remove caracteres inválidos (mantém letras com acento)
    # name = re.sub(r"[^\w\s-\<\>]", "", name, flags=re.UNICODE)
    name = re.sub(r"[^\w\s<>/\-.,]", "", name, flags=re.UNICODE)

    # snake_case → espaço
    name = name.replace("_", " ")

    # camelCase / PascalCase → separa com espaço
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)

    # capitaliza cada palavra
    return " ".join(word.capitalize() for word in name.split())

