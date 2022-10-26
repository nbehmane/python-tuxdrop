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

mainloop = None
bus = None
session_bus = None


def get_connected_devices(process_bus):
    object_manager = dbus.Interface(
        process_bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME, "/"),
        bluetooth_constants.DBUS_OM_IFACE
    )
    managed_objects = object_manager.GetManagedObjects()
    for path, ifaces in managed_objects.items():
        for iface_name in ifaces:
            if iface_name == bluetooth_constants.DEVICE_INTERFACE:
                device_properties = ifaces[bluetooth_constants.DEVICE_INTERFACE]
                if 'Connected' in device_properties:
                    is_connected = bluetooth_utils.dbus_to_python(device_properties['Connected'])
                    if is_connected:
                        try:
                            return path
                        except Exception as e:
                            print(e)
    return None


def obex_start():
    global mainloop
    global bus
    global session_bus

    mainloop = GLib.MainLoop()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    session_bus = dbus.SessionBus()

    try:
        device_path = get_connected_devices(bus)
        props = dbus.Interface(bus.get_object("org.bluez", device_path), "org.freedesktop.DBus.Properties")
        connected = bluetooth_utils.dbus_to_python(props.Get("org.bluez.Device1", "Connected"))
        if not connected:
            print("No device is connected. Please run again.")
            exit()
    except Exception as e:
        print(e)

    signal.signal(signal.SIGINT, ctrlc_handler)
    mainloop.run()


def ctrlc_handler(signum, frame):
    print("Quitting")
    global bus

    try:
        device_path = get_connected_devices(bus)
        if device_path is not None:
            device = dbus.Interface(bus.get_object("org.bluez", device_path), "org.bluez.Device1")
            print(f"Disconnecting from {device_path}")
            device.Disconnect()
    except Exception as e:
        print(e)

    mainloop.quit()