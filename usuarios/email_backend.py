import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for msg in email_messages:
            try:
                html = None
                for content, mimetype in getattr(msg, 'alternatives', []):
                    if mimetype == 'text/html':
                        html = content
                        break
                payload = {
                    "sender": {"name": "Signia", "email": "osorioescobardavidfelipe@gmail.com"},
                    "to": [{"email": to} for to in msg.to],
                    "subject": msg.subject,
                    "textContent": msg.body,
                }
                if html:
                    payload["htmlContent"] = html

                response = requests.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={
                        "api-key": settings.BREVO_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=15,
                )
                response.raise_for_status()
                sent += 1
            except Exception as e:
                if not self.fail_silently:
                    raise
        return sent