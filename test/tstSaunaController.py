__author__ = 'geurt'

import paho.mqtt.client as paho

def on_MQTTConnect(client, userdata, flags, rc):
    print "MQTTConnected, client: %s, userdata: %s, flags:% s and rc: %s" % (client,userdata,flags,rc)
    mqttClient.publish("sauna/saunatempcmd", str("100"), qos=2,retain=False)
    # quit()

if __name__ == '__main__':
    mqttURL = "HOST"
    mqttPort = "PORT"
    mqttClientID = "tester"

    mqttClient = paho.Client(client_id=mqttClientID)
    mqttClient.on_connect = on_MQTTConnect
    mqttClient.username_pw_set("user", "passwrd")
    mqttClient.connect(mqttURL, mqttPort)
    mqttClient.loop_forever()