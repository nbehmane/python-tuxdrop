import random
import sys
import signal

import dbus
import dbus.service
import dbus.mainloop.glib
import dbus.exceptions
from gi.repository import GLib
from PyOBEX.client import BrowserClient
import bluetooth

sys.path.insert(0, './bluetooth')

import bluetooth_utils
import bluetooth_constants
import bluetooth_exceptions
import bluetooth_gatt
import scan

mainloop = None
bus = None
session_bus = None

def ask(prompt):
    return input(prompt)



"""
class Transfer(dbus.service.Object):
    def __init__(self, session_bus, session_path, index, status="queued", name='None'):
        self.path = session_path + 'transfer' + str(index)
        self.status = status
        self.session = session_path
        self.name = name
        self.type = None
        self.time = None
        self.size = 0
        self.transferred = 0
        self.filename = None
        dbus.service.Object.__init__(self, session_bus, self.path)

    def get_properties(self):
        properties = dict()
        properties["Status"] = dbus.String(self.status)
        properties["Session"] = dbus.ObjectPath(self.session)
        properties["Name"] = dbus.String(self.name)
        properties["Size"] = dbus.UInt64(self.size)
        properties["Filename"] = dbus.String(self.filename)
        return {"org.bluez.obex.Transfer1": properties}

    @dbus.service.method("org.bluez.obex.Transfer1", in_signature='', out_signature='')
    def Cancel(self):
        print("Cancelling transfer.")

    @dbus.service.method("org.bluez.obex.Transfer1", in_signature='', out_signature='')
    def Suspend(self):
        self.status = "suspended"

    @dbus.service.method("org.bluez.obex.Transfer1", in_signature='', out_signature='')
    def Resume(self):
        print("Resuming transfer.")

    @dbus.service.method(bluetooth_constants.DBUS_PROPERTIES, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != "org.bluez.obex.Transfer1":
            raise bluetooth_exceptions.InvalidArgsException()
        return self.get_properties()["org.bluez.obex.Transfer1"]



class FileTransfer(dbus.service.Object):
    def __init__(self, ):
"""



class Agent(dbus.service.Object):
    def __init__(self, conn=None, obj_path=None):
        dbus.service.Object.__init__(self, conn, obj_path)
        self.pending_auth = False

    @dbus.service.method("org.bluez.obex.Agent1", in_signature="o", out_signature="s")
    def AuthorizePush(self, path):
        transfer = dbus.Interface(session_bus.get_object('org.bluez.obex', path),
                                  "org.freedesktop.DBus.Properties")
        properties = transfer.GetAll('org.bluez.obex.Transfer1')
        self.pending_auth = True
        auth = ask(f"Authorize ({path}, {properties['Name']}) (Y/n): ")
        if auth == "n" or auth == "N":
            self.pending_auth = False
            raise dbus.DBusException("org.bluez.obex.Error.Rejected", "Not Authorized")
        self.pending_auth = False
        return properties["Name"]

    @dbus.service.method("org.bluez.obex.Agent1", in_signature='', out_signature='')
    def Cancel(self):
        print("Authorization canceled")
        self.pending_auth = False


def interfaces_added(path, interfaces):
    print(f"{path} {interfaces}")
def interfaces_removed():
    print("REMOVED")

def error_cb(error):
    print(error)

def obex_start(filename, cmd="Get"):
    global mainloop
    global bus
    global session_bus

    print("Beginning OBEX session")

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = GLib.MainLoop()
    bus = dbus.SystemBus()
    session_bus = dbus.SessionBus()

    props = None
    device_address = None
    try:
        device_path = scan.get_connected_devices(bus)
        props = dbus.Interface(bus.get_object("org.bluez", device_path), "org.freedesktop.DBus.Properties")
        connected = bluetooth_utils.dbus_to_python(props.Get("org.bluez.Device1", "Connected"))
        device_address = bluetooth_utils.dbus_to_python(props.Get("org.bluez.Device1", "Address"))
        if not connected:
            print("No device is connected. Please run again.")
            exit(0)
    except Exception as e:
        print(e)

    obex_proxy_object = session_bus.get_object("org.bluez.obex", "/org/bluez/obex")
    client = dbus.Interface(obex_proxy_object, "org.bluez.obex.Client1")
    target_address = bluetooth_utils.dbus_to_python(props.Get("org.bluez.Device1", "Address"))
    print("Registering Agent")
    manager = dbus.Interface(session_bus.get_object("org.bluez.obex", "/org/bluez/obex"), "org.bluez.obex.AgentManager1")
    agent_path = "/test/agent"
    agent = Agent(session_bus, agent_path)
    manager.RegisterAgent(agent_path)

    if target_address is None:
        ctrlc_handler(0, 0)
    session_path = client.CreateSession(target_address, {"Target": "ftp", "Source": "38:BA:F8:55:8C:90"})
    print(session_path)
    obj = session_bus.get_object("org.bluez.obex", session_path)
    print(bluetooth_utils.dbus_to_python(obj))

    session_bus.add_signal_receiver(interfaces_added,
                            dbus_interface=bluetooth_constants.DBUS_OM_IFACE,
                            signal_name="InterfacesAdded")

    #ftp = dbus.Interface(obj, "org.bluez.obex.Transfer1")
    session = dbus.Interface(session_bus.get_object("org.bluez.obex", session_path), "org.bluez.obex.FileTransfer1")
    if cmd == "Get":
        print(f"Grabbing {filename}.")
        session.GetFile(filename, f"/home/nimab/.cache/obexd/{filename}")
    elif cmd == "Put":
        print(f"Sending {filename} over.")
        session.PutFile("/home/nimab/.cache/obexd/" + filename, filename)

    signal.signal(signal.SIGINT, ctrlc_handler)
    mainloop.run()


def ctrlc_handler(signum, frame):
    print("Quitting")
    global bus

    try:
        device_path = scan.get_connected_devices(bus)
        if device_path is not None:
            device = dbus.Interface(bus.get_object("org.bluez", device_path), "org.bluez.Device1")
            print(f"Disconnecting from {device_path}")
            device.Disconnect()
    except Exception as e:
        print(e)

    mainloop.quit()