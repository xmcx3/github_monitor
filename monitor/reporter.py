from os.path import basename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
import smtplib

class Reporter:
    def __init__(self, email_from, smtp_server, smtp_port, email_username=None, email_password=None):
        self.email_from = email_from
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_username = email_username
        self.email_password = email_password
        # TODO remove
        self.sent_emails_counter = 0

    def alert(self, subject, content, email_to_string, files=[]):

        # create email
        email = MIMEMultipart('alternative')
        # TODO calculate this value.
        email['Subject'] = subject
        email['From'] = self.email_from
        # email_to = email_to_string.split(',')
        email['To'] = email_to_string
        # part_text = MIMEText(text_version, 'plain', 'utf-8')
        # email.attach(part_text)
        part_html = MIMEText(content, 'html', 'utf-8')

        for fn in files:
            print basename(fn)
            with open(fn, "r") as f:
                part = MIMEApplication(
                    f.read(),
                )
            part.add_header('Content-Disposition', 'attachment',
                            filename=Header(basename(fn), 'utf-8').encode())
            email.attach(part)

        email.attach(part_html)

        self._send_email(email, email_to_string)

    def _send_email(self, email, email_to_string):
        mail_server = smtplib.SMTP(host=self.smtp_server, port=self.smtp_port)
        if int(self.smtp_port) != 25:
            mail_server = smtplib.SMTP_SSL(host=self.smtp_server, port=self.smtp_port)
        if self.email_username is not None:
            mail_server.login(self.email_username, self.email_password)
        try:
            mail_server.sendmail(self.email_from, email_to_string, email.as_string())
            self.sent_emails_counter += 1
        finally:
            mail_server.close()
