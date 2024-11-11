import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings

class EmailService:
    def __init__(self, to_email, subject, body):
        self.from_email = settings.EMAIL_HOST_USER
        self.to_email = to_email
        self.subject = subject
        self.body = body

    def send_email(self):
        
        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = self.to_email
        msg['Subject'] = self.subject
        msg.attach(MIMEText(self.body, 'plain'))

       
        text = msg.as_string()

        
        try:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()
            server.login(self.from_email, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(self.from_email, self.to_email, text)
            server.quit()
            print("Correo enviado exitosamente!")
        except Exception as e:
            print(f"Error: {e}")