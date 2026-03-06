from datetime import datetime
from django.conf import settings


class generateKeyOTP:
    @staticmethod
    def returnValue(phone):
        return str(phone) + str(datetime.date(datetime.now())) + settings.OTP_KEY
