import importlib

from django.conf import settings
from django.core.cache import cache
from django.apps import apps


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
        Traduz uma string com base no idioma atual.
        Aceita:
        - request (com header L)
        - código de idioma (ex: 'pt-pt')
        - None (fallback)
        """

        # -------------------
        # Resolver idioma
        # -------------------
        lang_code = None

        if hasattr(request_or_lang, 'headers'):
            lang_code = request_or_lang.headers.get('L')

        if isinstance(request_or_lang, str):
            lang_code = request_or_lang

        if not lang_code:
            lang_code = getattr(settings, 'LANGUAGE_CODE', 'en')

        lang_code = str(lang_code).lower().replace('-', '')

        cache_key = f"traducao:{lang_code}"

        # -------------------
        # Cache
        # -------------------
        cached = cache.get(cache_key)
        if cached and text in cached:
            return cached[text]

        traducoes = {}

        # -------------------
        # Base de dados (lazy)
        # -------------------
        try:
            from django_saas.models.traducao import Traducao

            db_trads = Traducao.objects.filter(
                idioma__code__iexact=lang_code
            )
            for t in db_trads:
                traducoes[t.chave] = t.traducao
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
        try:
            cache.set(cache_key, traducoes, 3600)
        except Exception:
            pass

        return traducoes.get(text, text)
