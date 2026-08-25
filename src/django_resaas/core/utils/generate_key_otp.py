import hashlib
import hmac
from datetime import datetime
from django.conf import settings


class generateKeyOTP:
    @staticmethod
    def returnValue(phone):
        message = f"{phone}:{datetime.date(datetime.now())}"

        return hmac.new(
            settings.OTP_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
