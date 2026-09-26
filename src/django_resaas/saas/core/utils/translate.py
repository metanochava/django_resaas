import importlib

from django.conf import settings
from django.core.cache import cache
from django.apps import apps


def _language_code(value):
    """'pt-pt' stays 'pt-pt'; a Language id (what the frontend sends in the
    L header, services/api.js) becomes its code. None when unknown."""
    if not value:
        return None
    value = str(value).strip()
    cache_key = f"translation:lang-code:{value}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    code = None
    try:
        from django_resaas.saas.models.language import Language

        code = (
            Language.objects.filter(code__iexact=value).values_list("code", flat=True).first()
            or _by_id(Language, value)
        )
    except Exception:
        code = None
    code = code or value
    try:
        cache.set(cache_key, code, 3600)
    except Exception:
        pass
    return code


def _by_id(Language, value):
    try:
        return Language.objects.filter(id=value).values_list("code", flat=True).first()
    except Exception:  # not an id of this model's type
        return None


class Translate:
    """
    Classe utilitária para tradução dinâmica:
    - Base de dados
    - Módulos lang
    - Cache
    """

    @staticmethod
    def tdc(request_or_lang, text):
        """
        Traduz uma string com base no language atual.
        Aceita:
        - request (com header L)
        - código de language (ex: 'pt-pt')
        - None (fallback)
        """

        # -------------------
        # Resolver language
        # -------------------
        lang_code = None

        # the L header carries the Language id (services/api.js) - resolve it
        # to the code the lang modules and Translation rows are keyed by
        if hasattr(request_or_lang, 'headers'):
            lang_code = _language_code(request_or_lang.headers.get('L'))

        if isinstance(request_or_lang, str):
            lang_code = _language_code(request_or_lang)

        if not lang_code:
            lang_code = getattr(settings, 'LANGUAGE_CODE', 'en')

        lang_code = str(lang_code).lower().replace('-', '')

        cache_key = f"translation:{lang_code}"

        # -------------------
        # Cache
        # -------------------
        cached = cache.get(cache_key)
        if cached and text in cached:
            return cached[text]
        if cached and text is not None:
            # same rule as the frontend's tdc(): case and surrounding spaces
            # do not make another key ("Latest vital signs" = "Latest Vital Signs")
            folded = cache.get(f"{cache_key}:folded")
            if folded is None:
                folded = {str(k).lower().strip(): v for k, v in cached.items()}
            return folded.get(str(text).lower().strip(), text)

        traducoes = {}

        # -------------------
        # Base de dados (lazy)
        # -------------------
        try:
            from django_resaas.saas.models.translation import Translation

            db_trads = Translation.objects.filter(
                language__code__iexact=lang_code
            )
            for t in db_trads:
                traducoes[t.chave] = t.translation
        except Exception:
            pass

        # -------------------
        # Módulos lang
        # -------------------
        for app in apps.get_app_configs():
            module_name = f"{app.name}.lang.{lang_code}"

            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                continue

            if hasattr(module, "key_value"):
                traducoes.update(module.key_value)

        # -------------------
        # Guardar cache
        # -------------------
        folded = {str(k).lower().strip(): v for k, v in traducoes.items()}
        try:
            cache.set(cache_key, traducoes, 3600)
            cache.set(f"{cache_key}:folded", folded, 3600)
        except Exception:
            pass

        if text in traducoes:
            return traducoes[text]
        return folded.get(str(text).lower().strip(), text) if text is not None else text
