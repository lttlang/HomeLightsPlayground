import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def sendEmailAlert(message):
    toAddr = os.getenv('MAINTAINER_EMAIL_USERNAME')
    fromAddr = os.getenv('MAINTAINER_EMAIL_USERNAME')
    pw = os.getenv('MAINTAINER_EMAIL_PW')
    if toAddr is None or pw is None:
        return
    msg = MIMEMultipart()
    msg['To'] = toAddr
    msg['From'] = fromAddr
    msg['Subject'] = "Home Lights MQTT Client Notification"
    msg.attach(MIMEText(message, 'plain'))
    text = msg.as_string()
    server = smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    server.login(fromAddr, pw)
    server.sendmail(fromAddr, toAddr, text)
    server.quit()
