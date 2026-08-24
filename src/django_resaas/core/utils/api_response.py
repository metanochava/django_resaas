from rest_framework.response import Response
from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils.clean import clean_name
from rest_framework.exceptions import PermissionDenied
            

class ApiResponse:

    @staticmethod
    def _msg(request, key):
        key = clean_name(key)
        return key if " " in key else Translate.tdc(request, key)

    @classmethod
    def ok(cls, request, key, status=200, **extra):
        return Response({
            "alert_success": cls._msg(request, key),
            **extra
        }, status=status)

    @classmethod
    def all(cls, request, status=200, **extra):
        return Response({
            **extra
        }, status=status)

    @classmethod
    def fail(cls, request, key, status=400, **extra):
        raise PermissionDenied( cls._msg(request, key) )


    @classmethod
    def warn(cls, request, key, status=200, **extra):
        return Response({
            "alert_warning": cls._msg(request, key),
            **extra
        }, status=status)

# ==============================
# Shortcuts (DX sugar 🔥)
# ==============================

def ok(request, key, **extra):
    return ApiResponse.ok(request, key, **extra)

def all(request, **extra):
    return ApiResponse.all(request, **extra)


def fail(request, key, **extra):
    return ApiResponse.fail(request, key, **extra)


def warn(request, key, **extra):
    return ApiResponse.warn(request, key, **extra)
