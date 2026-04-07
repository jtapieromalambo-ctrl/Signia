import ssl
import smtplib
from django.core.mail.backends.smtp import EmailBackend

class SSLEmailBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False
        try:
            context = ssl._create_unverified_context()
            self.connection = smtplib.SMTP_SSL(
                self.host, self.port,
                context=context,
                timeout=self.timeout,
            )
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise
