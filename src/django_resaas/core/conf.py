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
