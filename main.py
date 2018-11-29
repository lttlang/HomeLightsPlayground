import paho.mqtt.client as mqtt
import json, requests, os 
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
    print("connected with result code"+str(rc))

def on_subscribe(client, obj, mid, granted_qos):
    print("subscribed : "+str(mid)+ " "+str(granted_qos))

def on_message(client, userdata, msg):
    #print(msg.topic + " " + str(msg.payload)) 
    if not isNowInTimePeriod(time(17,30), time(23,0), datetime.utcnow().time()):
        return
    payload = json.loads(msg.payload)
    if 'objects' in payload:
        objects = payload['objects']
        for item in objects:
            if checkObjectIntersectsCamera(item):
                #do something for camera
                print('hello!')
                #getStateOfLights()
                return 

def on_log(client, obj, level, string):
    print(string)

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
    #print(str(jsonResponse))
    if jsonResponse[0]['power'] == 'off':
        turnOnLights()
    #else:
    #    turnOffLights()

def turnOnLights():
    payload = {
        "power": "on",
    }
    response = requests.post('https://api.lifx.com/v1/lights/all/state/delta', data=payload, headers=headers)
    print(response)

def turnOffLights():
    payload = {
        "power": "off",
    }
    response = requests.post('https://api.lifx.com/v1/lights/all/state/delta', data=payload, headers=headers)
    print(response)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe

client.on_log = on_log

#Still figuring out what to use for my broker
#url_str = os.environ.get('CLOUDMQTT_URL', 'mqtt://localhost:1883')
#url = urlparse(url_str)
#client.connect(url.hostname, url.port)

#client.subscribe(os.environ['CAMERA_MQTT_TOPIC'], 0)

#client.loop_start()

def main():
    app.run(debug=True, use_reloader=True)

if __name__ == '__main__':
    main()
