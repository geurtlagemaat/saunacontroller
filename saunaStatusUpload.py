#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'geurt'
import traceback
import time
import wiringpi as wiringpi
import Adafruit_DHT

DHT_SENSOR = Adafruit_DHT.DHT22

def doUpdate(NodeControl):
    """
        Sauna Status upload class. Publishes data to MQTT
    """
    NodeControl.log.debug("Saunastatus update")
    try:
        if ((NodeControl.getProperty("kachelstarteddatetime") != None) and (
                NodeControl.getProperty("kachelstarteddatetime") != -1) ):
            NodeControl.log.debug("publish sauna switched on")
            NodeControl.MQTTPublish(sTopic="sauna/switchedon", sValue="ON", iQOS=0, bRetain=False)
        else:
            NodeControl.log.debug("publish sauna switched off")
            NodeControl.MQTTPublish(sTopic="sauna/switchedon", sValue="OFF", iQOS=0, bRetain=False)

        if NodeControl.nodeProps.has_option('saunastatus', 'tempInSensorPath'):
            sInlaat = '{:.3f}'.format(
                getTemp(NodeControl, NodeControl.nodeProps.get('saunastatus', 'tempInSensorPath')) / float(1000))
            NodeControl.log.debug("Inlaat temperatuur: %s" % sInlaat)
            NodeControl.MQTTPublish(sTopic="sauna/inlaattemp", sValue=str(sInlaat), iQOS=0, bRetain=False)
        else:
            NodeControl.log.warning("Can not read inlet temp, no [sauna] tempInSensorPath configured")

        if NodeControl.nodeProps.has_option('saunastatus', 'tempSensorPath'):
            fCurrentSaunaTemp = getTemp(NodeControl,
                                        NodeControl.nodeProps.get('saunastatus', 'tempSensorPath')) / float(1000)
            sSauna = '{:.3f}'.format(fCurrentSaunaTemp)
            NodeControl.log.debug("Sauna temperatuur: %s" % sSauna)
            NodeControl.MQTTPublish(sTopic="sauna/temp", sValue=str(sSauna), iQOS=0, bRetain=False)
            NodeControl.setProperty("currenttemp", str(sSauna))
        else:
            NodeControl.log.warning("Can not read temp, no [sauna] tempInSensorPath configured")

        if wiringpi.digitalRead(25):
            NodeControl.MQTTPublish(sTopic="sauna/kachelstatus", sValue="ON", iQOS=2, bRetain=False)
            NodeControl.log.debug("current kachel status is on")
        else:
            NodeControl.MQTTPublish(sTopic="sauna/kachelstatus", sValue="OFF", iQOS=2, bRetain=False)
            NodeControl.log.debug("current kachel status is off")

        if ((NodeControl.getProperty("kachelstarteddatetime") != None) and (
                NodeControl.getProperty("kachelstarteddatetime") != -1) ):
            if ( (NodeControl.getProperty("settempcmd") != None) and (NodeControl.getProperty("settempcmd") != -1) ):
                NodeControl.log.debug("publish settempcmd: %s" % str(NodeControl.getProperty("settempcmd")))
                NodeControl.MQTTPublish(sTopic="sauna/settemp", sValue=str(NodeControl.getProperty("settempcmd")),
                                        iQOS=0, bRetain=False)
            else:
                NodeControl.log.debug("No settempcmd property available")
        else:
            NodeControl.log.debug("No kachelstarteddatetime property so no settemp")
            NodeControl.MQTTPublish(sTopic="sauna/settemp", sValue="-1", iQOS=0, bRetain=True)

        iAutoOffInt = -1
        if NodeControl.nodeProps.has_option('saunacontrol', 'autoSaunaOff'):
            iAutoOffInt = int(NodeControl.nodeProps.get('saunacontrol', 'autoSaunaOff'))
        if ((NodeControl.getProperty("kachelstarteddatetime") != None) and (
                NodeControl.getProperty("kachelstarteddatetime") != -1) ):
            if iAutoOffInt != -1:
                iKachelStartedDateTime = int(NodeControl.getProperty("kachelstarteddatetime"))
                iCurrentEpoch = int(time.time())
                iSwitchedOnSecs = (iCurrentEpoch - iKachelStartedDateTime)
                iSecondsLeft = iAutoOffInt - iSwitchedOnSecs
                NodeControl.log.debug("publish autoshutdown, time left: %s." % str(iSecondsLeft))
                NodeControl.MQTTPublish(sTopic="sauna/autoshutdown", sValue=str(iSecondsLeft), iQOS=0, bRetain=False)
            else:
                NodeControl.log.debug("publish autoshutdown, time left -1 (no auto shutdown.")
                NodeControl.MQTTPublish(sTopic="sauna/autoshutdown", sValue="-1", iQOS=0, bRetain=False)
        else:
            NodeControl.log.debug("No kachelstarteddatetime property available")
            NodeControl.MQTTPublish(sTopic="sauna/autoshutdown", sValue="-1", iQOS=0, bRetain=False)
        dhtTemp, dhtHum = getDHTData(NodeControl, 13)
        if dhtTemp is not None:
            NodeControl.MQTTPublish(sTopic="sauna/dht13/temp", sValue="{0:0.1f}".format(dhtTemp), iQOS=0, bRetain=False)
        if dhtHum is not None:
            NodeControl.MQTTPublish(sTopic="sauna/dht13/hum", sValue="{:.1f}".format(dhtHum), iQOS=0, bRetain=False)
        dhtTemp, dhtHum = getDHTData(NodeControl, 16)
        if dhtTemp is not None:
            NodeControl.MQTTPublish(sTopic="sauna/dht16/temp", sValue="{0:0.1f}".format(dhtTemp), iQOS=0,
                                    bRetain=False)
        if dhtHum is not None:
            NodeControl.MQTTPublish(sTopic="sauna/dht16/hum", sValue="{:.1f}".format(dhtHum), iQOS=0, bRetain=False)
        dhtTemp, dhtHum = getDHTData(NodeControl, 19)
        if dhtTemp is not None:
            NodeControl.MQTTPublish(sTopic="sauna/dht19/temp", sValue="{0:0.1f}".format(dhtTemp), iQOS=0,
                                    bRetain=False)
        if dhtHum is not None:
            NodeControl.MQTTPublish(sTopic="sauna/dht19/hum", sValue="{:.1f}".format(dhtHum), iQOS=0, bRetain=False)
    except Exception, exp:
        NodeControl.log.warning("Error sauna status update, error: %s." % (traceback.format_exc()))

def getTemp(NodeControl, sSensorPath):
    # Read ds18b20 sensors
    # TODO: move to lib generic
    try:
        f = open(sSensorPath, 'r')
        line = f.readline() # read 1st line
        crc = line.rsplit(' ', 1)
        crc = crc[1].replace('\n', '')
        if crc == 'YES':
            line = f.readline() # read 2nd line
            mytemp = line.rsplit('t=', 1)
        else:
            mytemp = 99999
        f.close()
        return int(mytemp[1])
    except Exception, exp:
        NodeControl.log.warning("Error reading sensor, path: %s, error: %s." % (sSensorPath, traceback.format_exc()))
        return 99999

def getDHTData(NodeControl, DHT_PIN):
    DHT_SENSOR = Adafruit_DHT.DHT22
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature is not None and humidity<=100:
        NodeControl.log.debug("Temp={0:0.1f}*C  Humidity={1:0.1f}%".format(temperature, humidity))
        return temperature, humidity
    else:
        return None, None