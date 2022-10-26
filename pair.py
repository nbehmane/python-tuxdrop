#!/usr/bin/python
# SPDX-License-Identifier: LGPL-2.1-or-later
from optparse import OptionParser
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GObject
import scan

sys.path.insert(0, './bluetooth')
import bluetooth_constants

BUS_NAME = 'org.bluez'
AGENT_INTERFACE = 'org.bluez.Agent1'
AGENT_PATH = "/test/agent"

bus = None
device_obj = None
dev_path = None
mainloop = None


def ask(prompt):
    return input(prompt)


def set_trusted(path):
    props = dbus.Interface(bus.get_object("org.bluez", path), "org.freedesktop.DBus.Properties")
    props.Set("org.bluez.Device1", "Trusted", True)


def dev_connect(path):
    dev = dbus.Interface(bus.get_object("org.bluez", path), "org.bluez.Device1")
    dev.Connect()


class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class Agent(dbus.service.Object):
    exit_on_release = True

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        print("Release")
        if self.exit_on_release:
            mainloop.quit()

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        authorize = ask("Authorize connection (yes/no): ")
        if (authorize == "yes"):
            return
        raise Rejected("Connection rejected by user")

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print("RequestPinCode (%s)" % (device))
        set_trusted(device)
        return ask("Enter PIN Code: ")

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print("RequestPasskey (%s)" % (device))
        set_trusted(device)
        passkey = ask("Enter passkey: ")
        return dbus.UInt32(passkey)

    @dbus.service.method(AGENT_INTERFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        print("DisplayPasskey (%s, %06u entered %u)" % (device, passkey, entered))

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print("DisplayPinCode (%s, %s)" % (device, pincode))

    @dbus.service.method(AGENT_INTERFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        confirm = ask("Confirm passkey (yes/no): ")
        if (confirm == "yes"):
            return
        raise Rejected("Passkey doesn't match")

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print("RequestAuthorization (%s)" % (device))
        auth = ask("Authorize? (yes/no): ")
        if (auth == "yes"):
            return
        raise Rejected("Pairing rejected")

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")


def pair_reply():
    print(f"Device paired {dev_path}")
    if (dev_path == None):
        mainloop.quit()
    set_trusted(dev_path)
    dev_connect(dev_path)
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
        capability = "KeyboardDisplay"
        path = "/test/agent"
        agent = Agent(bus, path)

        mainloop = GObject.MainLoop()

        obj = bus.get_object(BUS_NAME, "/org/bluez")
        manager = dbus.Interface(obj, "org.bluez.AgentManager1")
        manager.RegisterAgent(path, capability)
        print("Agent registered")

        device_proxy = bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME, device_paths[user_input])
        device_interface = dbus.Interface(device_proxy, bluetooth_constants.DEVICE_INTERFACE)
        agent.set_exit_on_release(False)
        device_interface.Pair(reply_handler=pair_reply, error_handler=pair_error, timeout=60000)
        device_obj = device_interface

        mainloop.run()
    except Exception as e:
        print("Input must be an integer.")
        print(e.get_dbus_name())
        print("Error: ", e.get_dbus_message())
        exit()

    #adapter.UnregisterAgent(path)
    #print("Agent unregistered")