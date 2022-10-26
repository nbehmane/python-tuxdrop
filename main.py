import sys

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import bluetooth
sys.path.insert(0, './bluetooth')

import bluetooth_utils
import bluetooth_constants
import scan
import connect
import pair
import advertise
import argument_parser
sys.path.insert(0, '.')

def main():
    args = argument_parser.parse_arguments()
    if (args.scan != None):
        print("Initiating scan")
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        scan.scan_devices(bus, args.scan * 1000)
        scan.scan_get_known_devices(bus)
    if (args.list == True):
        print("Printing known devices")
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        scan.scan_get_known_devices(bus)
    if (args.connect == True):
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
        except Exception as e:
            print("Input must be an integer.")
            exit()
        connect.connect(bus, device_paths[user_input], is_path=True)
    if (args.disconnect == True):
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
        except Exception as e:
            print("Input must be an integer.")
            exit()
        connect.disconnect(bus, device_paths[user_input], is_path=True)
    if (args.pair == True):
        pair.pair()
    if (args.advertise == True):
        advertise.advertise_start();


if __name__ == '__main__':
    main()