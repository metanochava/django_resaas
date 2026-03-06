from django.conf import settings
from django.template import loader
from django.template.exceptions import TemplateDoesNotExist


DEFAULT_TEMPLATES = {
    'REGISTER_CONFIRM': 'django_saas/email_confirmacao.html',
    'PASSWORD_RESET': 'django_saas/email_reset.html',
    'GENERIC_RESET': 'django_saas/email_template_reset.html',
}


def render_email_template(key, context):
    """
    Resolve template via settings com fallback para template da lib.
    """
    custom_templates = getattr(settings, 'DJANGO_REST_AUTH', {}).get('EMAIL_TEMPLATES', {})

    template_name = custom_templates.get(key, DEFAULT_TEMPLATES.get(key))

    try:
        return loader.render_to_string(template_name, context)
    except TemplateDoesNotExist:
        # fallback final de segurança
        return loader.render_to_string(DEFAULT_TEMPLATES[key], context)
