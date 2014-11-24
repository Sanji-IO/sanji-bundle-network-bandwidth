#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging

from sanji.core import Sanji
from sanji.connection.mqtt import Mqtt


REQ_RESOURCE = "/network/bandwidth"


class View(Sanji):

    # This function will be executed after registered.
    def run(self):

        for count in xrange(0, 100, 1):
            # Normal CRUD Operation
            #   self.publish.[get, put, delete, post](...)
            # One-to-One Messaging
            #   self.publish.direct.[get, put, delete, post](...)
            #   (if block=True return Message, else return mqtt mid number)
            # Agruments
            #   (resource[, data=None, block=True, timeout=60])

            # case 1: test PUT
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, data={"interface": "eth0"})
            if res.code != 200:
                print "data.enable=1 should reply code 200"
                print res.to_json()
                self.stop()

            # case 2: test GET
            print "GET %s" % REQ_RESOURCE + "/eth0"
            res = self.publish.get(REQ_RESOURCE + "/eth0")
            if res.code != 200:
                print "GET is not supported, code 200 is expected"
                self.stop()
            else:
                print res.to_json()

            # case 3: test PUT
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, data={"enable": 0})
            if res.code != 200:
                print "data.enable=1 should reply code 200"
                print res.to_json()
                self.stop()

            # case 4: test PUT
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, data={"enable": 1})
            if res.code != 200:
                print "data.enable=1 should reply code 200"
                print res.to_json()
                self.stop()

            # case 5: test GET
            print "GET %s" % REQ_RESOURCE + "/eth0"
            res = self.publish.get(REQ_RESOURCE + "/eth0")
            if res.code != 200:
                print "GET is not supported, code 200 is expected"
                self.stop()
            else:
                print res.to_json()

            # case 5: test PUT
            # print "PUT %s" % REQ_RESOURCE
            # res = self.publish.put(REQ_RESOURCE, data={"reset": 1})
            # if res.code != 200:
            #     print "data.enable=1 should reply code 200"
            #     print res.to_json()
            #     self.stop()

            # stop the test view
            self.stop()


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("Reboot")

    view = View(connection=Mqtt())
    view.start()
