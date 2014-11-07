#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import logging
import subprocess
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

        # try:
        #     bundle_env = kwargs["bundle_env"]
        # except KeyError:
        #     bundle_env = os.getenv("BUNDLE_ENV", "debug")

        if self.vnstat_start == 1:
            self.do_start()

    @Route(methods="get", resource="/network/monitor/:interface")
    def get_root(self, message, response):
        self.interface = message.param["interface"]
        return response(code=200, data={
            "info": subprocess.check_output("vnstat --xml -i " +
                                            message.param["interface"],
                                            shell=True),
            "enable": self.vnstat_start,
            "interface": self.interface})

    @Route(methods="put", resource="/network/monitor")
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

        if "reset" in message.data:
            if message.data["reset"] == 1:
                logger.debug("Reset network monitor statistic DB.")
                self.do_clean()

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
