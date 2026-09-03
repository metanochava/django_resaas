from django.conf import settings


DEFAULTS = {
    'FILE_TOKEN': {
        'KEY': 'None',
        'ENABLE_TEMPORARY': False,
        'TEMP_TTL': 300,
        'ENABLE_PERMANENT': True,
    },
    'CACHE_TIME': 300,
    'REQUIRE_FE_CREDENTIALS': False,
    'FRONT_END': {
        'REQUIRE_CREDENTIALS': False,
        'PUBLIC_URL': [],
        'URL_RULES': {},
        # 'allow' preserves the historical behavior for scopes with no
        # matching URL_RULES entry. Set to 'deny' for fail-closed.
        'DEFAULT_POLICY': 'allow',
    },
}


def _lookup(source, path):
    value = source

    for key in path.split('.'):
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None, False

    return value, True


def get_setting(path, default=None):
    """
    Exemplo:
    get_setting('FILE_TOKEN.KEY')
    get_setting('REQUIRE_FE_CREDENTIALS')
    """
    config = getattr(settings, 'DJANGO_REST_AUTH', {})

    value, found = _lookup(config, path)

    if found:
        return value

    value, found = _lookup(DEFAULTS, path)

    if found:
        return value

    return default
