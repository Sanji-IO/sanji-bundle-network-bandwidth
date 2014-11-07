#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../")
    from netmon import NetworkMonitor
except ImportError as e:
    print os.path.dirname(os.path.realpath(__file__)) + "/../"
    print sys.path
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))


class TestNetMonClass(unittest.TestCase):

    def setUp(self):
        def zombiefn():
            pass
        self.netmon = NetworkMonitor(connection=Mockup())
        self.netmon.do_start = zombiefn
        self.netmon.do_stop = zombiefn

    def tearDown(self):
        self.netmon = None

    @patch("netmon.subprocess")
    def test_put(self, subprocess):
        subprocess.check_output.return_value = True
        subprocess.call.return_value = True
        test_msg = {
            "id": 12345,
            "method": "put",
            "resource": "/network/monitor"
        }

        # case 1: no data attribute
        def resp1(code=200, data=None):
            self.assertEqual(400, code)
            self.assertEqual(data, {"message": "Invalid Input."})
        message = Message(test_msg)
        self.netmon.put_monitor(message, response=resp1, test=True)

        # case 2: data dict is empty or no enable exist
        def resp2(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = dict()
        message = Message(test_msg)
        self.netmon.put_monitor(message, response=resp2, test=True)

        # case 3: data
        def resp3(code=200, data=None):
            self.assertEqual(200, code)
        test_msg["data"] = {"reset": 1}
        message = Message(test_msg)
        self.netmon.put_monitor(message, response=resp3, test=True)

    def test2_put(self):
        test1_msg = {
            "id": 12365,
            "method": "get",
            "resource": "/network/monitor/eth1",
            "param": {"interface": "eth1"}
            }

        # case 4: data have interface
        def resp4(code=200, data=None):
            self.assertEqual(200, code)
        message = Message(test1_msg)
        with patch("netmon.subprocess") as subprocess:
            subprocess.check_output.return_value = True
            self.netmon.get_root(message, response=resp4, test=True)

        # case 5: data
        def resp5(code=200, data=None):
            self.assertEqual(200, code)
        test1_msg["data"] = {"enable": 1}
        message = Message(test1_msg)
        self.netmon.put_monitor(message, response=resp5, test=True)

        # case 6: data
        def resp6(code=200, data=None):
            self.assertEqual(200, code)
        test1_msg["data"] = {"enable": 0}
        message = Message(test1_msg)
        self.netmon.put_monitor(message, response=resp6, test=True)

    def test_do_start(self):
        self.netmon = NetworkMonitor(connection=Mockup())
        with patch("netmon.subprocess") as subprocess:
            subprocess.call.return_value = True
            self.netmon.do_start()
            subprocess.call.assert_called_once_with(
                self.netmon.VNSTAT_START, shell=True)

    def test_do_stop(self):
        self.netmon = NetworkMonitor(connection=Mockup())
        with patch("netmon.subprocess") as subprocess:
            subprocess.call.return_value = True
            self.netmon.do_stop()
            subprocess.call.assert_called_once_with(
                self.netmon.VNSTAT_STOP, shell=True)

    def test_init(self):
        with patch("netmon.ModelInitiator") as model:
            model.return_value.db.__getitem__.return_value = 1
            self.netmon.init()

if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger("Netmon Test")
    unittest.main()
