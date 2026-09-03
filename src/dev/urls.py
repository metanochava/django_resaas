"""
URL configuration for dev project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from django_resaas.engine.core.utils.autoload_urls import build_saas_urls

urlpatterns = [
    path('api/', include('django_resaas.urls')),
    path('api/demo/', include('dev.demo.urls')),
    path('admin/', admin.site.urls),
]

# Must run after the include() above, which is what actually imports every
# app's views (via django_resaas.urls -> hr.urls -> hr.views) and runs their
# @registerView decorators. Calling build_saas_urls() any earlier sees an
# empty VIEW_REGISTRY and silently produces no routes.
router, extra_patterns = build_saas_urls()
urlpatterns += [path('api/', include(router.urls))]
urlpatterns += extra_patterns
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)