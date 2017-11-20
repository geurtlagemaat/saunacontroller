__author__ = 'geurt'
import datetime
import traceback

from twisted.internet import reactor
from twisted.internet import task

from bliknetlib import nodeControl
import saunaStatusUpload
import saunaControl
import wiringpi as wiringpi


def saunaStatusUploadEvent(NodeControl):
    saunaStatusUpload.doUpdate(NodeControl)


if __name__ == '__main__':
    now = datetime.datetime.now()
    oNodeControl = nodeControl.nodeControl(r'settings/bliknetnode.conf')
    oNodeControl.log.info("BliknetNode: %s starting at: %s." % (oNodeControl.nodeID, now))

    # sauna status upload task
    if oNodeControl.nodeProps.has_option('saunastatus', 'active') and oNodeControl.nodeProps.getboolean('saunastatus',
                                                                                                        'active'):
        irUploadInt = 20
        if oNodeControl.nodeProps.has_option('saunastatus', 'uploadInterval'):
            iUploadInt = oNodeControl.nodeProps.getint('saunastatus', 'uploadInterval')
        oNodeControl.log.info("saunastatus upload task active, upload interval: %s" % str(iUploadInt))
        l = task.LoopingCall(saunaStatusUploadEvent, oNodeControl)
        l.start(irUploadInt)
    else:
        oNodeControl.log.info("saunastatus upload task not active.")

    if (oNodeControl.mqttClient != None):
        try:
            wiringpi.wiringPiSetupGpio()
            wiringpi.pinMode(25, 1)
        except Exception, exp:
            oNodeControl.log.error("Init GPIO init, error: %s" % traceback.format_exc())
        mySaunaController = saunaControl.saunaControl(oNodeControl)
        mySaunaController.doListen()

    oNodeControl.log.info("Starting reactor")
    reactor.run()
    oNodeControl.setProperty("kachelcmd", -1)
    oNodeControl.log.info("Shutting down, fail safe GPIO 25 to 0")
    wiringpi.digitalWrite(25, 0)
    saunaStatusUpload.doUpdate(oNodeControl)
    oNodeControl.MQTTPublish(sTopic="sauna/autoshutdown", sValue="0", iQOS=0, bRetain=True)
    oNodeControl.log.info("Shutting down, ready, bye!")
