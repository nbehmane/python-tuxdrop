import sys

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

sys.path.insert(0, './bluetooth')

import bluetooth_utils
import bluetooth_constants


def connect(bus, device_path, is_path):

    adapter_path = bluetooth_constants.BLUEZ_NAMESPACE + bluetooth_constants.ADAPTER_NAME
    if is_path == False:
        device_path = bluetooth_utils.device_address_to_path(device_path, adapter_path)
    device_proxy = bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME, device_path)
    device_interface = dbus.Interface(device_proxy,
                                      bluetooth_constants.DEVICE_INTERFACE)

    try:
        device_interface.Connect()
    except Exception as e:
        print("Connecting failed")
        print(e.get_dbus_name())
    else:
        print("Connection successful")
        return bluetooth_constants.RESULT_OK


def disconnect(bus, device_path, is_path):
    adapter_path = bluetooth_constants.BLUEZ_NAMESPACE + bluetooth_constants.ADAPTER_NAME
    if is_path == False:
        device_path = bluetooth_utils.device_address_to_path(device_path, adapter_path)
    device_proxy = bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME, device_path)
    device_interface = dbus.Interface(device_proxy,
                                      bluetooth_constants.DEVICE_INTERFACE)
    try:
        device_interface.Disconnect()
    except Exception as e:
        print("Failed to disconnect")
        print(e.get_dbus_name())
        print(e.get_dbus_message())
        return bluetooth_constants.RESULT_EXCEPTION
    else:
        print("Disconnected OK")
        return bluetooth_constants.RESULT_OK