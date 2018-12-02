import paho.mqtt.client as mqtt
import json, requests, os, pytz
import logging, logging.handlers
from urllib.parse import urlparse
import datetime
from flask import Flask
from emailalert import sendEmailAlert

#Hardcoded door coordinates.This is where we want to detect a person
DOOR_ZONE_X1 = 0.448958 
DOOR_ZONE_Y1 = 0.164815
DOOR_ZONE_X0 = 0.561980
DOOR_ZONE_Y0 = 0.482407

headers = {
    "Authorization": "Bearer %s" % os.environ['LIFX_AUTH_TOKEN'],
}

app = Flask(__name__)

lastDetectedTime = datetime.datetime.min

UNKNOWN = 0
EMPTY = 1
OCCUPIED = 2
currentApartmentState = UNKNOWN

def on_connect(client, userdata, flags, rc):
    logging.debug("connected with result code"+str(rc))

def on_subscribe(client, obj, mid, granted_qos):
    logging.debug("subscribed : "+str(mid)+ " "+str(granted_qos))

def on_message(client, userdata, msg):
    #logging.debug(msg.topic + " " + str(msg.payload))
    payload = json.loads(msg.payload)
    isPersonDetected = 'objects' in payload and len(payload['objects']) > 0
    global currentApartmentState
    global lastDetectedTime
    if isPersonDetected :
        #logging.debug("person detected")
        lastDetectedTime = datetime.datetime.now()
        #logging.debug("currentApartmentState: "+str(currentApartmentState))
        if currentApartmentState != OCCUPIED:
            #currentApartmentState = OCCUPIED
            triggerBulbOnFlow(payload['objects'])
    else:
        currentTime = datetime.datetime.now()
        elapsed = currentTime - lastDetectedTime
        #logging.debug("elapsed: "+str(elapsed)+" timedelta: "+str(datetime.timedelta(hours=1)))
        if elapsed >= datetime.timedelta(minutes=10) and currentApartmentState != EMPTY:
            currentApartmentState = EMPTY
            logging.debug("Apartment is now empty")
            sendEmailAlert("Apartment is now empty")
            return #for now, we can do some logic to turn off lights here
        else:
            #don't do anything
            return

def triggerBulbOnFlow(objects):
    global currentApartmentState
    pst = pytz.timezone('America/Los_Angeles')
    start = datetime.time(17, 0, tzinfo=pst)
    end = datetime.time(0, 0, tzinfo=pst)
    now = datetime.datetime.now(pst)
    if not isNowInTimePeriod(start, end, now.time()):
        #logging.debug(str(now.time()) + "not in time range")
        return
    #logging.debug("in time range")
    for item in objects:
        if checkObjectIntersectsCamera(item):
            #do something for camera
            currentApartmentState = OCCUPIED
            logging.debug("Apartment is now occupied")
            sendEmailAlert("Apartment is now occupied")
            getStateOfLights()
            break

def on_log(client, obj, level, string):
    logging.debug(string)

def checkObjectIntersectsCamera(item):
    logging.debug(str(item['x1']) + ", " + str(item['x0']) +", "+
                  str(item['y1']) + ", "+ str(item['y0']))
    x_mid = (DOOR_ZONE_X0 - DOOR_ZONE_X1) / 2 + DOOR_ZONE_X1
    y_mid = (DOOR_ZONE_Y0 - DOOR_ZONE_Y1) / 2 + DOOR_ZONE_Y1
    #logging.debug("x_mid: "+ str(x_mid))
    #logging.debug("y_mid: " + str(y_mid))
    return item['x1'] < x_mid and x_mid < item['x0'] and item['y1'] < y_mid and y_mid < item['y0']

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
    logging.debug("turning on lights response: " +str(response))

def turnOffLights():
    sendEmailAlert("Turning lights off")
    payload = {
        "power": "off",
    }
    response = requests.post('https://api.lifx.com/v1/lights/all/state/delta', data=payload, headers=headers)
    logging.debug(str(response))

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
