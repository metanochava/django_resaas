"""RESAAS API exceptions.

They ARE DRF APIExceptions (so DRF keeps deciding the HTTP status and the
handler in handler.py turns them into the RESAAS error contract); they only add
the two optional things the contract has room for: a stable machine-readable
`code` and structured `details`.

    raise ConflictError("This profile is already assigned.", code="group_already_assigned")

`code` is technical and never translated; the message may be (it goes through
Translate.tdc in the handler). Do not invent a code just to fill the field.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class ResaasAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request could not be completed."
    default_code = "error"

    def __init__(self, detail=None, code=None, details=None, status_code=None):
        super().__init__(detail=detail, code=code)

        # the RESAAS `code` is only what the caller stated - never DRF's generic "error"
        self.resaas_code = code
        self.resaas_details = details

        if status_code is not None:
            self.status_code = status_code


class ConflictError(ResaasAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state of the resource."
