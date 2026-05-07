import resend
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        resend.api_key = settings.RESEND_API_KEY
        sent = 0
        for msg in email_messages:
            try:
                body = msg.body
                html = None
                for content, mimetype in getattr(msg, 'alternatives', []):
                    if mimetype == 'text/html':
                        html = content
                        break
                params = {
                    "from": msg.from_email,
                    "to": msg.to,
                    "subject": msg.subject,
                    "text": body,
                }
                if html:
                    params["html"] = html
                resend.Emails.send(params)
                sent += 1
            except Exception as e:
                if not self.fail_silently:
                    raise
        return sent