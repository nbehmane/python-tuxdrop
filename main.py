import sys

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import bluetooth
import obex
from PyOBEX.server import BrowserServer

sys.path.insert(0, './bluetooth')

import bluetooth_utils
import bluetooth_constants
import scan
import connect
import pair
import advertise
import argument_parser
sys.path.insert(0, '.')
def select_device_path(bus):
    scan.scan_get_known_devices(bus)
    device_paths = list(scan.devices.keys())
    i = 0
    for path in device_paths:
        print(f"{i}: {path}")
        i += 1
    done = 0
    while not done:
        try:
            user_input = int(input("Device Index: "))
            done = 1
        except Exception as e:
            print("Input must be an integer.")
    return device_paths[user_input]

def main():
    args = argument_parser.parse_arguments()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    if (args.scan != None):
        print("Initiating scan")
        scan.scan_devices(bus, args.scan * 1000)
        scan.scan_get_known_devices(bus)
    if (args.list == True):
        print("Printing known devices")
        scan.scan_get_known_devices(bus)
    if (args.connect == True):
        device_path = select_device_path(bus)
        connect.connect(bus, device_path=device_path, is_path=True)
    if (args.disconnect == True):
        device_path = select_device_path(bus)
        connect.disconnect(bus, device_path=device_path, is_path=True)
    if (args.pair == True):
        pair.pair()
    if (args.advertise == True):
        advertise.advertise_start();
        if (args.put != None):
            obex.obex_start(args.put, 'Put')
        elif (args.get != None):
            obex.obex_start(args.get, 'Get')


        #session_bus = dbus.SessionBus()
        #client = dbus.Interface(session_bus.get_object("org.bluez.obex", "/org/bluez/obex", ), 'org.bluez.obex.Client1')
        #print("Creating session...")
        #obex_session = client.CreateSession(path, {"Target": "ftp"})


if __name__ == '__main__':
    main()