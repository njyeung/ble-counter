import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from storage import store_device

AGENT_INTERFACE = "org.bluez.Agent1"
AGENT_PATH = "/upl/agent"

class Agent(dbus.service.Object):
    def __init__(self, bus, path):
        super().__init__(bus, path)
        self.bus = bus

        # Tracks devices that are mid-pairing
        # Dedups malicious attempts to pair twice
        self.pending_devices = set()


    # Extracts MAC from device_path
    #
    # input: /org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF 
    # output: AA:BB:CC:DD:EE:FF
    def _extract_mac(self, device_path):
        return device_path.split("/")[-1].replace("dev_", "").replace("_", ":")

    # Disconnect device
    # We don't remove it because we want to preserve the IRK for identity resolution
    def _disconnect(self, device_path):
        try:
            device = self.bus.get_object("org.bluez", device_path)
            device.Disconnect(dbus_interface="org.bluez.Device1")
        except:
            pass

    # Once device announces it has been "paired",
    # wait a few seconds for key exchange and bonding to happen
    # then disconnect the device
    def _accept_and_watch(self, device):
        if device in self.pending_devices:
            return
        self.pending_devices.add(device)

        def on_properties_changed(interface, changed, invalidated):
            if interface == "org.bluez.Device1" and changed.get("Paired"):
                def disconnect_and_cleanup():
                    self._disconnect(device)
                    self.pending_devices.discard(device)
                GLib.timeout_add_seconds(3, disconnect_and_cleanup)

        self.bus.add_signal_receiver(
            on_properties_changed,
            signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties",
            path=device
        )

    # REJECT ALL SERVICE REQUESTS - no profile access is allowed
    # This blocks standard bluetooth profiles (keystroke injection, audio streaming, files)
    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        self._disconnect(device) # DISCONNECT IMMEDIATELY
        raise dbus.DBusException("org.bluez.Error.Rejected", "Rejected")


    # Remote devices send us pairing requests.
    # We accept them all to allow bonding (so BlueZ gets the IRK),
    # then disconnect immediately when bonding completes.
    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def RequestConfirmation(self, device, passkey):
        mac = self._extract_mac(device)
        store_device(mac, str(passkey))
        self._accept_and_watch(device)

        print(f"CONFIRMATION REQUEST:")
        print(f"    MAC: {mac}")
        print(f"    PASSKEY: {passkey}")

        return  # accept

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    adapter = bus.get_object("org.bluez", "/org/bluez/hci0")
    adapter_props = dbus.Interface(adapter, "org.freedesktop.DBus.Properties")
    adapter_iface = dbus.Interface(adapter, "org.bluez.Adapter1")

    print("Setting up adapter...")
    adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))
    adapter_props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))
    adapter_props.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(True))
    print("Adapter is powered and discoverable")

    agent = Agent(bus, AGENT_PATH)

    agent_manager = dbus.Interface(
        bus.get_object("org.bluez", "/org/bluez"),
        "org.bluez.AgentManager1"
    )
    agent_manager.RegisterAgent(AGENT_PATH, "DisplayYesNo")
    agent_manager.RequestDefaultAgent(AGENT_PATH)

    adapter_iface.StartDiscovery()
    print("Discovery started")

    main_loop = GLib.MainLoop()
    try:
        main_loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nCleaning up...")

        try:
            adapter_iface.StopDiscovery()
        except:
            pass
        
        
        adapter_props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(False))
        
        try:
            agent_manager.UnregisterAgent(AGENT_PATH)
        except:
            pass
        
        print("Done!")


if __name__ == "__main__":
    main()
