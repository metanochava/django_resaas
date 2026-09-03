"""
Best-effort Entity branding for the unauthenticated email flows
(registration OTP, password reset) - there is no RESAAS tenant context
yet at these endpoints (no X-RESAAS-Context header, the user isn't
logged in), so the tenant can't be read off `request.entity_id` the way
BaseAPIView does. Instead this resolves the Entity by matching the
request's Origin host against `Entity.site` - the same "one entity per
frontend origin" assumption the old registration view already made via
`request.META['HTTP_ORIGIN']`.

Returns `(entity_name, logo_url)` - both `None` when nothing resolves
(unknown origin, no Entity for that site, or the Entity has no logo /
has `display_logo_login=False`) - every email template here treats a
missing logo as a normal, expected case, not an error.
"""


def _origin_host(request):
    origin = request.META.get("HTTP_ORIGIN", "") if request else ""
    if not origin:
        return ""
    # "https://app.example.com:8080" -> "app.example.com"
    return origin.split("//")[-1].split("/")[0].split(":")[0]


def resolve_email_branding(request):
    if not request:
        return None, None

    host = _origin_host(request)
    if not host:
        return None, None

    from django_resaas.engine.models.entity import Entity

    entity = Entity.objects.filter(site=host).first()
    if not entity:
        return None, None

    logo_url = None
    if entity.display_logo_login and entity.logo:
        try:
            logo_url = request.build_absolute_uri(entity.logo.url)
        except ValueError:
            logo_url = None

    return entity.name, logo_url
