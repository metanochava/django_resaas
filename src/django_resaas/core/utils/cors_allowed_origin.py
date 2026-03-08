def get_cors_origins():
    try:
        from django_resaas.models.cors_allowed_origin import CorsAllowedOrigin
        return list(CorsAllowedOrigin.objects.values_list("origin", flat=True))
    except Exception:
        return []