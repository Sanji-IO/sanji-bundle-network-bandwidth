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

    PUT_SCHEMA = Schema([{
        "enable": All(int, Range(min=0, max=1)),
        "reset": All(int, Range(min=0, max=1)),
        "interface": All(str, Length(255)),
        "threshold": int
    }], extra=REMOVE_EXTRA)

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.model = ModelInitiator("netmon", path_root)
        self.interface = self.model.db["interface"]
        self.vnstat_start = self.model.db["enable"]
        self.threshold = self.model.db["threshold"]

        if self.vnstat_start == 1:
            self.do_start()

    def read_bandwidth(self):
        subprocess.call(["vnstat", "-u", "-i", self.interface])
        tmp = subprocess.check_output("vnstat --xml -i " +
                                      self.interface +
                                      "|grep -m 1 total", shell=True)
        root = ET.fromstring(tmp)
        count = 0
        for item in root:
            count += int(item.text)
        _logger.debug("Read Bandwidth %s" % count)
        return count

    # This function will be executed after registered.
    def run(self):

        while True:
            # message of today
            motd = 0
            count = self.read_bandwidth()
            if count < self.threshold:
                sleep(60)
                continue

            while True:
                if motd == 0:
                    _logger.debug(
                        "Reach limited threshold %s" % self.threshold)
                    self.publish.event.put(
                        "/network/bandwidth/event",
                        data={
                            "info": self.read_bandwidth(),
                            "enable": self.vnstat_start,
                            "interface": self.interface,
                            "threshold": self.threshold
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
                "enable": self.vnstat_start,
                "interface": self.interface,
                "threshold": self.threshold
            })

    @Route(methods="put", resource="/network/bandwidth", schema=PUT_SCHEMA)
    def put_monitor(self, message, response):
        if not hasattr(message, "data"):
            return response(code=400, data={"message": "Invalid Input."})

        if "enable" in message.data:
            if message.data["enable"] == 1:
                self.do_start()
            else:
                self.do_stop()
            self.model.db["enable"] = message.data["enable"]
            self.vnstat_stat = message.data["enable"]

        if "reset" in message.data:
            if message.data["reset"] == 1:
                _logger.debug("Reset network monitor statistic DB.")
                self.do_clean()

        if "interface" in message.data:
            if self.model.db["interface"] != message.data["interface"]:
                self.do_clean(start=False)
            self.model.db["interface"] = message.data["interface"]
            self.interface = message.data["interface"]

        if "threshold" in message.data:
            self.model.db["threshold"] = message.data["threshold"]
            self.threshold = message.data["threshold"]

        self.model.save_db()
        return response(data=self.model.db)

    def do_start(self):
        _logger.debug("Start network monitor.")
        self.vnstat_start = 1
        subprocess.call(["vnstat", "-u", "-i", self.interface])
        subprocess.call(self.VNSTAT_START, shell=True)

    def do_stop(self):
        _logger.debug("Stop network monitor.")
        self.vnstat_start = 0
        subprocess.call(self.VNSTAT_STOP, shell=True)

    def do_clean(self, start=True):
        _logger.debug("Clean vnstat with interface %s" % (self.interface,))
        self.do_stop()
        subprocess.call(
            ["vnstat", "--delete", "--force", "-i", self.interface])

        if start is False:
            return

        _logger.debug("Update vnstat with interface %s" % (self.interface,))
        subprocess.call(["vnstat", "-u", "-i", self.interface])
        self.do_start()


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    _logger = logging.getLogger("sanji.networkmonitor")

    netbmon = NetworkMonitor(connection=Mqtt())
    netbmon.start()
