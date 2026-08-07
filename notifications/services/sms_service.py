import requests
import logging
from django.conf import settings
from notifications.models.sms_log import SMSLog

logger = logging.getLogger('caldan.sms')


class SMSService:
    """Handles SMS sending via Africa's Talking with Celcom fallback."""

    @classmethod
    def send(cls, phone_number, message, user=None, notification_type='GENERAL'):
        """Send SMS with automatic provider failover."""
        # Normalize phone number
        phone = cls._normalize_phone(phone_number)

        # Check if real SMS is enabled
        if not getattr(settings, 'SEND_REAL_SMS', False):
            logger.info(f"[DEV MODE] SMS would be sent to {phone}: {message[:50]}...")
            cls._log_attempt(phone, message, 'DEV_MODE', user=user, notification_type=notification_type)
            return True

        # Try primary provider
        provider = getattr(settings, 'SMS_PROVIDER', 'africastalking')

        if provider == 'celcom':
            result = cls._send_celcom(phone, message)
        else:
            result = cls._send_africastalking(phone, message)

        # Log attempt
        cls._log_attempt(
            phone, message,
            'SENT' if result['success'] else 'FAILED',
            provider=provider,
            provider_response=result.get('response', ''),
            user=user,
            notification_type=notification_type
        )

        # If failed, try fallback
        if not result['success'] and provider == 'africastalking':
            logger.warning("Africa's Talking failed, trying Celcom fallback")
            result = cls._send_celcom(phone, message)
            cls._log_attempt(
                phone, message,
                'SENT' if result['success'] else 'FAILED',
                provider='celcom',
                provider_response=result.get('response', ''),
                user=user,
                notification_type=notification_type
            )

        return result['success']

    @classmethod
    def _send_africastalking(cls, phone, message):
        """Send SMS via Africa's Talking."""
        try:
            url = "https://api.africastalking.com/version1/message"
            headers = {
                "apikey": settings.AFRICASTALKING_API_KEY,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
            data = {
                "username": settings.AFRICASTALKING_USERNAME,
                "to": phone,
                "message": message,
                "from": "CALDAN",
            }
            response = requests.post(url, headers=headers, data=data, timeout=30)
            result = response.json()
            if response.status_code == 200 and result.get('status') == 'success':
                return {'success': True, 'response': result}
            else:
                return {'success': False, 'response': result}
        except Exception as e:
            return {'success': False, 'response': str(e)}

    @classmethod
    def _send_celcom(cls, phone, message):
        """Send SMS via Celcom Africa."""
        try:
            url = settings.CELCOM_API_URL
            headers = {"Content-Type": "application/json"}
            data = {
                "api_key": settings.CELCOM_API_KEY,
                "partner_id": settings.CELCOM_PARTNER_ID,
                "shortcode": settings.CELCOM_SHORTCODE,
                "mobile": phone,
                "message": message,
            }
            response = requests.post(url, json=data, headers=headers, timeout=30)
            result = response.json()
            if response.status_code == 200 and result.get('status') == 'success':
                return {'success': True, 'response': result}
            else:
                return {'success': False, 'response': result}
        except Exception as e:
            return {'success': False, 'response': str(e)}

    @classmethod
    def _normalize_phone(cls, phone):
        """Normalize Kenyan phone number to international format."""
        phone = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if phone.startswith('07') or phone.startswith('01'):
            return '+254' + phone[1:]
        elif phone.startswith('7') or phone.startswith('1'):
            return '+254' + phone
        elif phone.startswith('254'):
            return '+' + phone
        elif phone.startswith('+254'):
            return phone
        else:
            return phone

    @classmethod
    def _log_attempt(cls, phone, message, status, provider='', provider_response='', user=None, notification_type='GENERAL'):
        """Log SMS attempt to database."""
        try:
            SMSLog.objects.create(
                recipient_phone=phone,
                message=message[:500],
                status=status,
                provider=provider,
                provider_response=provider_response[:500],
                user=user,
                notification_type=notification_type,
            )
        except Exception as e:
            logger.error(f"Failed to log SMS attempt: {str(e)}")