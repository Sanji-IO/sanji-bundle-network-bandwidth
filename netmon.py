#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import logging
import subprocess
import xml.etree.ElementTree as ET
from time import sleep
from datetime import datetime
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from sanji.model_initiator import ModelInitiator


# TODO: logger should be defined in sanji package?
logger = logging.getLogger()


class NetworkMonitor(Sanji):
    VNSTAT_START = "/etc/init.d/vnstat start"
    VNSTAT_STOP = "/etc/init.d/vnstat stop"

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.model = ModelInitiator("netmon", path_root)
        self.interface = "eth0"
        self.vnstat_start = self.model.db["enable"]
        self.threshold = self.model.db["threshold"]

        # try:
        #     bundle_env = kwargs["bundle_env"]
        # except KeyError:
        #     bundle_env = os.getenv("BUNDLE_ENV", "debug")

        if self.vnstat_start == 1:
            self.do_start()

    def read_bandwidth(self):
            tmp = subprocess.check_output("vnstat --xml -i " +
                                          self.interface +
                                          "|grep -m 1 total", shell=True)
            root = ET.fromstring(tmp)
            count = 0
            for item in root:
                count += int(item.text)
            logger.debug("total %s" % count)
            return count

    # This function will be executed after registered.
    def run(self):

        while True:
            time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.debug("time: %s" % time_str)
            # message of today
            motd = 0
            count = self.read_bandwidth()
            if count > self.threshold:
                while True:
                    if motd == 0:
                        logger.debug("Threshold %s" % self.threshold)
                        # event would not have response
                        # self.publish.event("/remote/sanji/events",
                        # data={"message": "Time: %s" % time_str})
                    if (motd >= 86400) or (self.read_bandwidth() == 0):
                        break
                    else:
                        motd += 1

                    sleep(1)

            sleep(60)

    @Route(methods="get", resource="/network/bandwidth")
    def get_root(self, message, response):
            return response(code=200, data={
                "info": self.read_bandwidth(),
                "enable": self.vnstat_start,
                "interface": self.interface,
                "threshold": self.threshold})

    @Route(methods="put", resource="/network/bandwidth")
    def put_monitor(self, message, response):
        # TODO: status code should be added into error message
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
                logger.debug("Reset network monitor statistic DB.")
                self.do_clean()

        if "interface" in message.data:
            self.model.db["interface"] = message.data["interface"]
            self.interface = message.data["interface"]

        if "threshold" in message.data:
            self.model.db["threshold"] = message.data["threshold"]
            self.threshold = message.data["threshold"]

        self.model.save_db()
        return response()

    def do_start(self):
        logger.debug("Start network monitor.")
        self.vnstat_start = 1
        subprocess.call(self.VNSTAT_START, shell=True)

    def do_stop(self):
        logger.debug("Stop network monitor.")
        self.vnstat_start = 0
        subprocess.call(self.VNSTAT_STOP, shell=True)

    def do_clean(self):
        self.do_stop()
        subprocess.call("vnstat --delete --force  -i " +
                        self.interface, shell=True)
        subprocess.call("vnstat -u -i " + self.interface, shell=True)
        self.do_start()


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("Network Bandwidth Monitor")

    netbmon = NetworkMonitor(connection=Mqtt())
    netbmon.start()
