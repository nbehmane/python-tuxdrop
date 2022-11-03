import random
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
import bluetooth_exceptions
import bluetooth_gatt
import scan

mainloop = None
bus = None
session_bus = None

def ask(prompt):
    return input(prompt)


class Agent(dbus.service.Object):
    def __init__(self, conn=None, obj_path=None):
        dbus.service.Object.__init__(self, conn, obj_path)
        self.pending_auth = False

    @dbus.service.method("org.bluez.obex.Transfer1", in_signature="o", out_signature="s")
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

class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        print("Adding TemperatureService to the Application")
        self.add_service(TemperatureService(bus, '/org/bluez/ldsg', 0))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(bluetooth_constants.DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        print('GetManagedObjects')

        for service in self.services:
            print("GetManagedObjects: service="+service.get_path())
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response

class TemperatureService(bluetooth_gatt.Service):
    #   Fake micro:bit temperature service that simulates temperature sensor measurements
    #   ref: https://lancaster-university.github.io/microbit-docs/resources/bluetooth/bluetooth_profile.html
    #   temperature_period characteristic not implemented to keep things simple

    def __init__(self, bus, path_base, index):
        print("Initialising TemperatureService object")
        bluetooth_gatt.Service.__init__(self, bus, path_base, index, bluetooth_constants.TEMPERATURE_SVC_UUID, True)
        print("Adding TemperatureCharacteristic to the service")
        self.add_characteristic(TemperatureCharacteristic(bus, 0, self))

class TemperatureCharacteristic(bluetooth_gatt.Characteristic):
    temperature = 0
    delta = 0
    notifying = False

    def __init__(self, bus, index, service):
        bluetooth_gatt.Characteristic.__init__(
            self, bus, index,
            bluetooth_constants.TEMPERATURE_CHR_UUID,
            ['read','notify'],
            service)
        self.notifying = False
        self.temperature = random.randint(0, 50)
        print("Initial temperature set to "+str(self.temperature))
        self.delta = 0
        GLib.timeout_add(1000, self.simulate_temperature)

    def simulate_temperature(self):
        self.delta = random.randint(-1, 1)
        self.temperature = self.temperature + self.delta
        if (self.temperature > 50):
            self.temperature = 50
        elif (self.temperature < 0):
            self.temperature = 0
        print("simulated temperature: "+str(self.temperature)+"C")
        if self.notifying:
            self.notify_temperature()

    def ReadValue(self, options):
        print('ReadValue in TemperatureCharacteristic called')
        print('Returning '+str(self.temperature))
        value = []
        value.append(dbus.Byte(self.temperature))
        return value

    # called by timer expiry
    # simulated temperature will fluctuate between 0 and 50 degrees celsius with randomly selected
    # deltas of at most +/- 5 degrees

    def notify_temperature(self):
        value = []
        value.append(dbus.Byte(self.temperature))
        print("notifying temperature="+str(self.temperature))
        self.PropertiesChanged(bluetooth_constants.GATT_CHARACTERISTIC_INTERFACE, { 'Value': value }, [])
        return self.notifying

    # note this overrides the same method in bluetooth_gatt.Characteristic where it is exported to
    # make it visible over DBus
    def StartNotify(self):
        print("starting notifications")
        self.notifying = True

    def StopNotify(self):
        print("stopping notifications")
        self.notifying = False

def register_app_cb():
    print("GATT application registered")

def register_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()



def obex_start():
    global mainloop
    global bus
    global session_bus

    print("Beginning OBEX session")

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = GLib.MainLoop()
    bus = dbus.SystemBus()
    session_bus = dbus.SessionBus()

    """
    client = dbus.Interface(session_bus.get_object("org.bluez.obex", '/org/bluez/obex', ),
                            'org.bluez.obex.Client1')

    print("Creating Session")
    try:
        path = client.CreateSession("/org/bluez/hci0/dev_5C_87_30_66_F4_35", {"Target": "ftp"})
    except Exception as e:
        print(e)
    """

    props = None
    try:
        device_path = scan.get_connected_devices(bus)
        props = dbus.Interface(bus.get_object("org.bluez", device_path), "org.freedesktop.DBus.Properties")
        connected = bluetooth_utils.dbus_to_python(props.Get("org.bluez.Device1", "Connected"))
        if not connected:
            print("No device is connected. Please run again.")
            exit(0)
    except Exception as e:
        print(e)

    """
    app = Application(bus)
    print("Registering GATT application")
    service_manager = dbus.Interface(bus.get_object(bluetooth_constants.BLUEZ_SERVICE_NAME, "/org/bluez/hci0"),
                                     bluetooth_constants.GATT_MANAGER_INTERFACE)
    service_manager.RegisterApplication(app.get_path(), {}, reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)
    """
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
    obj = session_bus.get_object("org.bluez.obex", session_path)
    ftp = dbus.Interface(obj, "org.bluez.obex.Transfer1")


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