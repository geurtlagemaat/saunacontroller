__author__ = 'geurt'

import time
import traceback

from twisted.internet import task
from twisted.internet import reactor

import wiringpi as wiringpi
import saunaStatusUpload


class saunaControlError(Exception):
    pass


class saunaControl(object):
    """
    Sauna Control class. MQTT connection: subscribes to MQTT. All *cmd are commands
    """
    def __init__(self, NodeControl):
        self._NodeControl = NodeControl
        self._lCall = None
        self.subscribeTopics()

    def doListen(self):
        self._NodeControl.mqttClient.on_message = self.on_message
        self._NodeControl.mqttClient.loop_start()

    def subscribeTopics(self):
        self._NodeControl.mqttClient.on_subscribe = self.on_subscribe
        self._NodeControl.mqttClient.subscribe("sauna/kachelcmd", 0);
        self._NodeControl.mqttClient.subscribe("sauna/saunatempcmd", 0);
        self._NodeControl.mqttClient.subscribe("sauna/saunastatusupdatecmd", 0);

    def on_subscribe(self, client, userdata, mid, granted_qos):
        self._NodeControl.log.info("Subscribed: " + str(mid) + " " + str(granted_qos))

    def on_message(self, client, userdata, msg):
        self._NodeControl.log.info("ON MESSAGE:" + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
        if (msg.topic == "sauna/kachelcmd"):
            sCMD = str(msg.payload)
            if (sCMD == "AAN") and ((self._NodeControl.getProperty("kachelcmd") == None) or (
                    self._NodeControl.getProperty("kachelcmd") == -1) ):
                iDefSaunaTemp = 90
                if self._NodeControl.nodeProps.has_option('saunacontrol', 'defaulttemp'):
                    iDefSaunaTemp = self._NodeControl.nodeProps.getint('saunacontrol', 'defaulttemp')
                self._NodeControl.log.debug("Set default temp to: %s" % iDefSaunaTemp)
                self._NodeControl.setProperty("settempcmd", iDefSaunaTemp)
                self._NodeControl.setProperty("kachelstarteddatetime", time.time())
                self._NodeControl.setProperty("kachelcmd", 1)
                self.saunaControlEvent()
                # set control event interval
                self._lCall = task.LoopingCall(self.saunaControlEvent)
                self._lCall.start(5)
                self._NodeControl.log.debug("Sauna aan")
                if self._NodeControl.nodeProps.has_option('saunacontrol', 'autoSaunaOff'):
                    fAutoOffInt = float(self._NodeControl.nodeProps.get('saunacontrol', 'autoSaunaOff'))
                    self._NodeControl.log.debug("Set auto shut down to: %s" % str(fAutoOffInt))
                    reactor.callLater(fAutoOffInt, self.saunaAutoShutDownOffEvent)
            elif (sCMD == "UIT"):
                self._NodeControl.setProperty("kachelcmd", -1)
                self.saunaControlEvent()
        if (msg.topic == "sauna/saunatempcmd"):
            self._NodeControl.log.debug("Set temp to: %s" % str(msg.payload))
            self._NodeControl.setProperty("settempcmd", msg.payload)
        if (msg.topic == "sauna/saunastatusupdatecmd"):
            self._NodeControl.log.debug("saunastatusupdatecmd request, msg: %s" % str(msg.payload))
            print "saunastatusupdatecmd"
            self.saunaControlEvent()
        saunaStatusUpload.doUpdate(self._NodeControl)

    def saunaControlEvent(self):
        try:
            if self._NodeControl.getProperty("kachelcmd") == 1:
                self._NodeControl.log.debug("kachelcmd is on")
                iDesiredTemp = 0
                if ((self._NodeControl.getProperty("settempcmd") != None) and (
                        self._NodeControl.getProperty("settempcmd") != -1) ):
                    self._NodeControl.log.debug(
                        "read settempcmd property: %s" % self._NodeControl.getProperty("settempcmd"))
                    iDesiredTemp = int(self._NodeControl.getProperty("settempcmd"))
                else:
                    raise saunaControlError, 'no valid Desired temperature'
                fCurrentTemp = 0
                if ((self._NodeControl.getProperty("currenttemp") != None) and (
                        self._NodeControl.getProperty("currenttemp") != -1) ):
                    fCurrentTemp = float(self._NodeControl.getProperty("currenttemp"))
                else:
                    raise saunaControlError, 'no valid current temperature'
                self._NodeControl.log.debug(
                    "saunaControlEvent, desired temp: %s, current temp: %s" % (str(iDesiredTemp), str(fCurrentTemp)))
                if float(fCurrentTemp) < int(iDesiredTemp):
                    self._NodeControl.log.debug("desired temp to low")
                    if wiringpi.digitalRead(25):
                        self._NodeControl.log.debug("desired temp to low, heating already on")
                    else:
                        wiringpi.digitalWrite(25, 1)
                        self._NodeControl.log.debug("desired temp to low, heating switched on")
                else:
                    self._NodeControl.log.debug("desired temp to high")
                    if wiringpi.digitalRead(25):
                        wiringpi.digitalWrite(25, 0)
                        self._NodeControl.log.debug("desired temp to high, heating switched off")
                    else:
                        self._NodeControl.log.debug("desired temp to high, heating already switched off")
            else:
                self._NodeControl.log.debug("kachelcmd off")
                wiringpi.digitalWrite(25, 0)
                self._NodeControl.setProperty("kachelstarteddatetime", -1)
                self._NodeControl.setProperty("settempcmd", -1)
                if self._lCall != None:
                    self._lCall.stop()
                    self._lCall = None
        except Exception, exp:
            wiringpi.digitalWrite(25, 0)
            saunaStatusUpload.doUpdate(self._NodeControl)
            self._NodeControl.log.error("Error sauna controller, switched off. Error: %s." % (traceback.format_exc()))

    def saunaAutoShutDownOffEvent(self):
        self._NodeControl.log.debug("Auto shut down event")
        try:
            self._NodeControl.setProperty("kachelcmd", -1)
            self.saunaControlEvent()
        except Exception, exp:
            self._NodeControl.log.warning("Error auto shutdown, error: %s." % traceback.format_exc())