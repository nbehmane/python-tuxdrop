import sys
import signal
from time import sleep

sys.path.insert(0, './bluetooth')
import bluetooth_constants
import bluetooth_exceptions
import dbus
import dbus.exceptions
import dbus.service
import dbus.mainloop.glib
import pair
from gi.repository import GLib

bus = None
adapter_path = None
adv_mgr_interface = None
mainloop = GLib.MainLoop()
dev_path = None
session_bus = None
client = None
obex_session = None

global dev_obj


class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/pybex/advertisement'

    def __init__(self, bus, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids = ['0x1106']
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.local_name = 'PyBex'
        self.include_tx_power = False
        self.include_tx_power = False
        self.data = None
        self.discoverable = True
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids, signature='s')
        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data, signature='sv')
        if self.local_name is not None:
            properties['LocalName'] = dbus.String(self.local_name)
        if self.discoverable is not None and self.discoverable == True:
            properties['Discoverable'] = dbus.Boolean(self.discoverable)
        if self.include_tx_power:
            properties['Includes'] = dbus.Array(['tx-power'], signature='s')
        if self.data is not None:
            properties['Data'] = dbus.Dictionary(self.data, signature='yv')
        print(properties)
        return {bluetooth_constants.ADVERTISING_MANAGER_INTERFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(bluetooth_constants.DBUS_PROPERTIES, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != bluetooth_constants.ADVERTISEMENT_INTERFACE:
            raise bluetooth_exceptions.InvalidArgsException()
        return self.get_properties()[bluetooth_constants.ADVERTISING_MANAGER_INTERFACE]

    @dbus.service.method(bluetooth_constants.ADVERTISING_MANAGER_INTERFACE, in_signature='', out_signature='')
    def Release(self):
        print(f'{self.path} Released')


def advertise_register_cb():
    print("Advertisement registered.")


def advertise_register_error_cb(error):
    print(f"Error: Failed to register advertisement: {error}")
    mainloop.quit()


def advertise_start():
    global adv
    global adv_mgr_interface
    bus.add_signal_receiver(advertise_properties_changed_signal,
                            dbus_interface=bluetooth_constants.DBUS_PROPERTIES,
                            signal_name="PropertiesChanged",
                            path_keyword="path")

    bus.add_signal_receiver(advertise_interfaces_added_signal,
                            dbus_interface=bluetooth_constants.DBUS_OM_IFACE,
                            signal_name="InterfacesAdded")

    print("Registering advertisement ", adv.get_path())
    adv_mgr_interface.RegisterAdvertisement(adv.get_path(), {}, reply_handler=advertise_register_cb,
                                            error_handler=advertise_register_error_cb)
    print(f"Advertisement {adv.local_name} activated.")
    print(f"Registering Agent")
    obj = bus.get_object("org.bluez", "/org/bluez")
    manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    agent_path = "/pybex/agent"
    capability = "KeyboardDisplay"
    agent = pair.Agent(bus, agent_path)
    manager.RegisterAgent(agent_path, capability)
    agent.set_exit_on_release(False)
    print("Agent registered")
    signal.signal(signal.SIGINT, ctrlc_handler)
    mainloop.run()


def set_trusted(path):
    props = dbus.Interface(bus.get_object("org.bluez", path), "org.freedesktop.DBus.Properties")
    props.Set("org.bluez.Device1", "Trusted", True)


def dev_connect(path):
    dev = dbus.Interface(bus.get_object("org.bluez", path), "org.bluez.Device1")
    dev.Connect()


def advertise_set_connected_status(path, status):
    global connected
    global dev_path
    global dev_obj
    if (status == 1):
        print("-" * 40)
        print(f'{path} Connected')
        print("-" * 40)
        connected = 1
        advertise_stop()
    else:
        print("Disconnected")
        connected = 0
        mainloop.quit()


def advertise_set_paired_status(path, paired):
    global session_bus
    global client
    global obex_session
    if (paired == 1):
        print(f"{path} is paired.")
        session_bus = dbus.SessionBus()
        client = dbus.Interface(session_bus.get_object("org.bluez.obex", "/org/bluez/obex", ), 'org.bluez.obex.Client1')
        print("Creating session...")
        obex_session = client.CreateSession(path, {"Target": "ftp"})

        # Once paired, this is where the obex code will go.

    else:
        print(f"{path} is not paired.")


def advertise_properties_changed_signal(interface, changed, invalidated=None, path=None):
    try:
        if (interface == bluetooth_constants.DEVICE_INTERFACE):
            if ("Connected" in changed):
                advertise_set_connected_status(path, changed["Connected"])
            if ("Paired" in changed):
                advertise_set_paired_status(path, changed["Paired"])
    except Exception as e:
        print(e)


def advertise_interfaces_added_signal(path, interfaces):
    if bluetooth_constants.DEVICE_INTERFACE in interfaces:
        properties = interfaces[bluetooth_constants.DEVICE_INTERFACE]
        if ("Connected" in properties):
            advertise_set_connected_status(path, properties["Connected"])
        if ("Paired" in properties):
            advertise_set_paired_status(path, properties["Paired"])


def advertise_stop():
    global adv
    global adv_mgr_interface
    print("Unregistering advertisement ", adv.get_path())
    adv_mgr_interface.UnregisterAdvertisement(adv.get_path())


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
adapter_path = bluetooth_constants.BLUEZ_NAMESPACE + bluetooth_constants.ADAPTER_NAME
adv_mgr_interface = dbus.Interface(bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME, adapter_path),
                                   bluetooth_constants.ADVERTISING_MANAGER_INTERFACE)
adv = Advertisement(bus, 0, 'peripheral')


def ctrlc_handler(signum, frame):
    print("Quitting")
    advertise_stop()
    mainloop.quit()

# https://stackoverflow.com/questions/68547083/python-opp-obex-server-using-bluez-obex-and-pydbus