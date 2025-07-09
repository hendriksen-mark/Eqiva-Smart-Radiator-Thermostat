from bleak.backends.scanner import BLEDevice

class Listener():

    def onScanSeen(self, device: BLEDevice) -> None:

        pass

    def onScanFound(self, device: BLEDevice) -> None:

        pass

    def onConnected(self, device: BLEDevice) -> None:

        pass

    def onDisconnected(self, device: BLEDevice) -> None:

        pass

    def onRequest(self, device: BLEDevice) -> None:

        pass

    def onNotify(self, device: BLEDevice, bytes: bytearray) -> None:

        pass
