# This is a sample Python script.
import sys

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

sys.path.insert(0, './bluetooth')

import bluetooth_utils
import bluetooth_constants

sys.path.insert(0, '.')

adapter_interface = None
mainloop = None
timer_id = None
managed_objects_found = 0
devices = {}


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


def scan_get_known_devices(bus):
    global managed_objects_found
    object_manager = dbus.Interface(
        bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME, "/"),
        bluetooth_constants.DBUS_OM_IFACE
    )

    managed_objects = object_manager.GetManagedObjects()

    for path, ifaces in managed_objects.items():
        for iface_name in ifaces:
            if iface_name == bluetooth_constants.DEVICE_INTERFACE:
                managed_objects_found += 1
                print("Object Path: ", path)
                device_properties = ifaces[bluetooth_constants.DEVICE_INTERFACE]
                devices[path] = device_properties
                if 'Address' in device_properties:
                    print("Address: ",
                          bluetooth_utils.dbus_to_python(device_properties['Address']))
                if 'Name' in device_properties:
                    print("Name: ",
                          bluetooth_utils.dbus_to_python(device_properties['Name']))
                print('-' * 40)


def scan_list_devices():
    for path in devices:
        dev = devices[path]
        print(bluetooth_utils.dbus_to_python(dev['Address']))


def scan_properties_changed_signal(interface, changed, invalidated, path):
    if interface != bluetooth_constants.DEVICE_INTERFACE:
        return
    if path in devices:
        devices[path] = dict(devices[path].items())
        devices[path].update(changed.items())
    else:
        devices[path] = changed

    dev = devices[path]
    print('Changed Path: ', path)
    if 'Address' in dev:
        print('Changed Address: ',
              bluetooth_utils.dbus_to_python(dev['Address']))
    if 'Name' in dev:
        print('Changed Name: ',
              bluetooth_utils.dbus_to_python(dev['Name']))
    if 'RSSI' in dev:
        print('RSSI: ',
              bluetooth_utils.dbus_to_python(dev['RSSI']))

    print('-' * 45)


def scan_interfaces_removed_signal(path, interfaces):
    # interfaces is an array of dictionary strings in this signal
    if not bluetooth_constants.DEVICE_INTERFACE in interfaces:
        return
    if path in devices:
        dev = devices[path]
        if 'Address' in dev:
            print('Removing Address: ',
                  bluetooth_utils.dbus_to_python(dev['Address']))
        if 'Name' in dev:
            print('Removing Name: ',
                  bluetooth_utils.dbus_to_python(dev['Name']))
        del devices[path]
        print('-' * 45)


def scan_interfaces_added_signal(path, interfaces):
    if not bluetooth_constants.DEVICE_INTERFACE in interfaces:
        return
    device_properties = interfaces[bluetooth_constants.DEVICE_INTERFACE]
    if path not in devices:
        print("Object Path: ", path)
        devices[path] = device_properties
        dev = devices[path]
        if 'Address' in dev:
            print('Address: ',
                  bluetooth_utils.dbus_to_python(dev['Address']))
        if 'Name' in dev:
            print('Name: ',
                  bluetooth_utils.dbus_to_python(dev['Name']))
        if 'RSSI' in dev:
            print('RSSI: ',
                  bluetooth_utils.dbus_to_python(dev['RSSI']))

        print('-' * 45)


def scan_timeout_signal():
    global adapter_interface
    global mainloop
    global timer_id
    GLib.source_remove(timer_id)
    mainloop.quit()
    adapter_interface.StopDiscovery()
    bus = dbus.SystemBus()
    bus.remove_signal_receiver(scan_interfaces_added_signal, "InterfacesAdded")
    bus.remove_signal_receiver(scan_interfaces_removed_signal, "InterfacesRemoved")
    bus.remove_signal_receiver(scan_properties_changed_signal, "PropertiesChanged")
    return True


def scan_devices(bus, timeout):
    global adapter_interface
    global mainloop
    global timer_id
    adapter_path = bluetooth_constants.BLUEZ_NAMESPACE + bluetooth_constants.ADAPTER_NAME

    adapter_object = bus.get_object(
        bluetooth_constants.BLUEZ_SERVICE_NAME,
        adapter_path
    )

    adapter_interface = dbus.Interface(
        adapter_object,
        bluetooth_constants.ADAPTER_INTERFACE
    )

    bus.add_signal_receiver(
        scan_interfaces_added_signal,
        dbus_interface=bluetooth_constants.DBUS_OM_IFACE,
        signal_name='InterfacesAdded'
    )

    bus.add_signal_receiver(
        scan_interfaces_removed_signal,
        dbus_interface=bluetooth_constants.DBUS_OM_IFACE,
        signal_name="InterfacesRemoved"
    )

    bus.add_signal_receiver(
        scan_properties_changed_signal,
        dbus_interface=bluetooth_constants.DBUS_PROPERTIES,
        signal_name="PropertiesChanged",
        path_keyword="path"
    )

    mainloop = GLib.MainLoop()
    timer_id = GLib.timeout_add(timeout, scan_timeout_signal)

    adapter_interface.StartDiscovery(byte_arrays=True)
    mainloop.run()