import sys
import signal

import dbus
import dbus.service
import dbus.mainloop.glib
import dbus.exceptions
from gi.repository import GLib
import bluetooth

sys.path.insert(0, './bluetooth')

import bluetooth_utils
import bluetooth_constants
import scan

mainloop = None
bus = None
session_bus = None


def obex_start():
    global mainloop
    global bus
    global session_bus

    print("Beginning OBEX session")

    mainloop = GLib.MainLoop()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    session_bus = dbus.SessionBus()

    try:
        device_path = scan.get_connected_devices(bus)
        props = dbus.Interface(bus.get_object("org.bluez", device_path), "org.freedesktop.DBus.Properties")
        connected = bluetooth_utils.dbus_to_python(props.Get("org.bluez.Device1", "Connected"))
        if not connected:
            print("No device is connected. Please run again.")
            exit(0)
    except Exception as e:
        print(e)

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