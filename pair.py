#!/usr/bin/python
# SPDX-License-Identifier: LGPL-2.1-or-later
from optparse import OptionParser
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GObject
import scan
import agent

sys.path.insert(0, './bluetooth')
import bluetooth_constants

BUS_NAME = 'org.bluez'
AGENT_INTERFACE = 'org.bluez.Agent1'
AGENT_PATH = "/test/agent"

bus = None
device_obj = None
dev_path = None
mainloop = None


def pair_reply():
    print(f"Device paired {dev_path}")
    if (dev_path == None):
        mainloop.quit()
    agent.set_trusted(dev_path)
    agent.dev_connect(dev_path)
    mainloop.quit()


def pair_error(error):
    err_name = error.get_dbus_name()
    if err_name == "org.freedesktop.DBus.Error.NoReply" and device_obj:
        print("Timed out. Cancelling pairing")
        device_obj.CancelPairing()
    else:
        print("Creating device failed: %s" % (error))
    mainloop.quit()


def pair():
    global bus
    global mainloop
    global device_obj
    print("Initiating pairing")
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    scan.scan_get_known_devices(bus)
    device_paths = list(scan.devices.keys())
    i = 0
    for path in device_paths:
        print(f"{i}: {path}")
        i += 1
    try:
        user_input = int(input("Device Index: "))
        mainloop = GObject.MainLoop()
        agent_obj = agent.agent_register(bus, mainloop)

        device_proxy = bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME, device_paths[user_input])
        device_interface = dbus.Interface(device_proxy, bluetooth_constants.DEVICE_INTERFACE)
        agent_obj.set_exit_on_release(False)
        device_interface.Pair(reply_handler=pair_reply, error_handler=pair_error, timeout=60000)
        device_obj = device_interface
        mainloop.run()
    except Exception as e:
        print("Input must be an integer.")
        print(e.get_dbus_name())
        print("Error: ", e.get_dbus_message())
        exit()

    # adapter.UnregisterAgent(path)
    # print("Agent unregistered")