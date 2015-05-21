#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import logging
import subprocess
import xml.etree.ElementTree as ET
from time import sleep
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from sanji.model_initiator import ModelInitiator

from voluptuous import Schema
from voluptuous import REMOVE_EXTRA
from voluptuous import Range
from voluptuous import All
from voluptuous import Length

_logger = logging.getLogger("sanji.networkmonitor")


class NetworkMonitor(Sanji):
    VNSTAT_START = "/etc/init.d/vnstat start"
    VNSTAT_STOP = "/etc/init.d/vnstat stop"

    PUT_SCHEMA = Schema({
        "enable": All(int, Range(min=0, max=1)),
        "reset": All(int, Range(min=0, max=1)),
        "interface": All(str, Length(1, 255)),
        "threshold": int
    }, extra=REMOVE_EXTRA)

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.model = ModelInitiator("netmon", path_root)

        if self.model.db["enable"] == 1:
            self.do_start()

    def read_bandwidth(self):
        subprocess.call(["vnstat", "-u", "-i", self.model.db["interface"]])
        tmp = subprocess.check_output("vnstat --xml -i " +
                                      self.model.db["interface"] +
                                      "|grep -m 1 total", shell=True)
        root = ET.fromstring(tmp)
        count = 0
        for item in root:
            count += int(item.text)
        _logger.debug(
            "Interface: %s Read Bandwidth %s" %
            (self.model.db["interface"], count))
        return count

    # This function will be executed after registered.
    def run(self):

        while True:
            # message of today
            motd = 0
            count = self.read_bandwidth()
            if count < self.model.db["threshold"]:
                sleep(60)
                continue

            while True:
                if motd == 0:
                    _logger.debug(
                        "Interface: %s Reach limited threshold %s" %
                        (self.model.db["interface"],
                            self.model.db["threshold"]))

                    self.publish.event.put(
                        "/network/bandwidth/event",
                        data={
                            "info": self.read_bandwidth(),
                            "enable": self.model.db["enable"],
                            "interface": self.model.db["interface"],
                            "threshold": self.model.db["threshold"]
                        })

                if motd >= 5 or self.read_bandwidth() == 0:
                    break

                motd += 1
                sleep(60)

    @Route(methods="get", resource="/network/bandwidth")
    def get_root(self, message, response):
        return response(
            data={
                "info": self.read_bandwidth(),
                "enable": self.model.db["enable"],
                "interface": self.model.db["interface"],
                "threshold": self.model.db["threshold"]
            })

    @Route(methods="put", resource="/network/bandwidth", schema=PUT_SCHEMA)
    def put_monitor(self, message, response):
        if not hasattr(message, "data"):
            return response(code=400, data={"message": "Invalid Input."})

        if "reset" in message.data and message.data["reset"] == 1:
            self.do_clean(start=False)

        if "interface" in message.data:
            if self.model.db["interface"] != message.data["interface"]:
                self.do_clean(start=False)
            self.model.db["interface"] = message.data["interface"]

        if "threshold" in message.data:
            self.model.db["threshold"] = message.data["threshold"]

        if "enable" in message.data:
            if message.data["enable"] == 1:
                self.do_start()
            else:
                self.do_stop()
            self.model.db["enable"] = message.data["enable"]

        self.model.save_db()
        return response(data=self.model.db)

    def do_start(self):
        _logger.info("Start network monitor.")
        subprocess.call(["vnstat", "-u", "-i", self.model.db["interface"]])
        subprocess.call(self.VNSTAT_START, shell=True)

    def do_stop(self):
        _logger.info("Stop network monitor.")
        subprocess.call(self.VNSTAT_STOP, shell=True)

    def do_clean(self, start=True):
        _logger.info(
            "Clean vnstat with interface %s" % (self.model.db["interface"],))
        self.do_stop()
        subprocess.call(
            ["vnstat", "--delete", "--force", "-i",
             self.model.db["interface"]])

        if start is False:
            return

        _logger.debug(
            "Update vnstat with interface %s" % (self.model.db["interface"],))
        subprocess.call(["vnstat", "-u", "-i", self.model.db["interface"]])
        self.do_start()


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    _logger = logging.getLogger("sanji.networkmonitor")

    netbmon = NetworkMonitor(connection=Mqtt())
    netbmon.start()
