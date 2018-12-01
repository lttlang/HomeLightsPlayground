import paho.mqtt.client as mqtt
import json, requests, os, pytz
import logging, logging.handlers
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlparse
from datetime import datetime, time
from flask import Flask

#Hardcoded door coordinates.This is where we want to detect a person
DOOR_ZONE_X1 = 0.448958 
DOOR_ZONE_Y1 = 0.164815
DOOR_ZONE_X0 = 0.561980
DOOR_ZONE_Y0 = 0.482407

headers = {
    "Authorization": "Bearer %s" % os.environ['LIFX_AUTH_TOKEN'],
}

app = Flask(__name__)

def on_connect(client, userdata, flags, rc):
    logging.debug("connected with result code"+str(rc))

def on_subscribe(client, obj, mid, granted_qos):
    logging.debug("subscribed : "+str(mid)+ " "+str(granted_qos))

def on_message(client, userdata, msg):
    #logging.debug(msg.topic + " " + str(msg.payload)) 
    pst = pytz.timezone('America/Los_Angeles')
    start = time(17, 0, tzinfo=pst)
    end = time(23, 0, tzinfo=pst)
    now = datetime.now(pst)
    if not isNowInTimePeriod(start, end, now.time()):
        #logging.debug(str(now.time()) + "not in time range")
        return
    #logging.debug("in time range")
    payload = json.loads(msg.payload)
    if 'objects' in payload:
        objects = payload['objects']
        for item in objects:
            if checkObjectIntersectsCamera(item):
                #do something for camera
                getStateOfLights()
                return 

def on_log(client, obj, level, string):
    logging.debug(string)

def checkObjectIntersectsCamera(item):
     left = max(DOOR_ZONE_X1, item['x1'])
     right = min(DOOR_ZONE_X0, item['x0'])
     bottom = max(DOOR_ZONE_Y1, item['y1'])
     top = min(DOOR_ZONE_Y0, item['y0'])
     return left < right and bottom < top
 
def isNowInTimePeriod(startTime, endTime, nowTime):
    if startTime < endTime:
        return nowTime >= startTime and nowTime <= endTime
    else: #Over midnight
        return nowTime >= startTime or nowTime <= endTime

def getStateOfLights():
    response = requests.get('https://api.lifx.com/v1/lights/all', headers=headers)
    jsonResponse = response.json()
    logging.debug("state of lights response: "+str(jsonResponse))
    if jsonResponse[0]['power'] == 'off':
        logging.debug("lights were off, turning them on")
        turnOnLights()

def turnOnLights():
    sendEmailAlert("Turning on lights")
    payload = {
        "power": "on",
    }
    response = requests.post('https://api.lifx.com/v1/lights/all/state/delta', data=payload, headers=headers)
    logging.debug("turning on lights response: " +response)

def turnOffLights():
    sendEmailAlert("Turning lights off")
    payload = {
        "power": "off",
    }
    response = requests.post('https://api.lifx.com/v1/lights/all/state/delta', data=payload, headers=headers)
    logging.debug(response)

def sendEmailAlert(message):
    toAddr = os.environ['MAINTAINER_EMAIL_USERNAME']
    fromAddr = os.environ['MAINTAINER_EMAIL_USERNAME']
    msg = MIMEMultipart()
    msg['To'] = toAddr
    msg['From'] = fromAddr
    msg['Subject'] = "Home Lights MQTT Client Notification"
    msg.attach(MIMEText(message, 'plain'))
    text = msg.as_string()
    server = smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    server.login(fromAddr, os.environ['MAINTAINER_EMAIL_PW'])
    server.sendmail(fromAddr, toAddr, text)
    server.quit()

handler = logging.handlers.WatchedFileHandler("myapp.log")
formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s")
handler.setFormatter(formatter)
root = logging.getLogger()
root.setLevel("DEBUG")
root.addHandler(handler)

sendEmailAlert('Starting client')

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe

#client.on_log = on_log
url_str = os.environ.get('CLOUDMQTT_URL', 'mqtt://localhost:1883')
url = urlparse(url_str)
client.connect(url.hostname, url.port)

client.subscribe(os.environ['CAMERA_MQTT_TOPIC'], 0)

client.loop_start()

def main():
    app.run(debug=True, use_reloader=True)

if __name__ == '__main__':
    main()
