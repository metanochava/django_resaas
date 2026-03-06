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


def get_setting(path, default=None):
    """
    Exemplo:
    get_setting('FILE_TOKEN.KEY')
    get_setting('REQUIRE_FE_CREDENTIALS')
    """
    config = getattr(settings, 'DJANGO_REST_AUTH', {})

    for key in path.split('.'):
        if isinstance(config, dict) and key in config:
            config = config[key]
        else:
            return default

    return config
