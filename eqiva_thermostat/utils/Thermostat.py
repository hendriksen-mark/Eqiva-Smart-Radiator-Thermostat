from datetime import datetime
import asyncio
from bleak import BleakClient

from .Listener import Listener
from .Program import Program
from .Temperature import Temperature
from .Vacation import Vacation
from .Mode import Mode
from .OpenWindowConfig import OpenWindowConfig
from .EqivaException import EqivaException

import logManager

LOGGER = logManager.logger.get_logger(__name__)

class Thermostat(BleakClient, Listener):

    MAC_PREFIX = "00:1A:22:"
    WAIT_NOTIFICATION = 2

    CHARACTERISTIC_DEVICE_NAME_STRING = "00002a24-0000-1000-8000-00805f9b34fb"
    CHARACTERISTIC_VENDOR_STRING = "00002a29-0000-1000-8000-00805f9b34fb"
    CHARACTERISTIC_REQUEST_HANDLE = "3fa4585a-ce4a-3bad-db4b-b8df8179ea09"
    CHARACTERISTIC_NOTIFICATION_HANDLE = "d0e8434d-cd29-0996-af41-6c90f4e0eb2a"

    COMMAND_SERIAL = [0x00]
    COMMAND_STATUS = [0x03]
    COMMAND_VACATION = [0x40]
    COMMAND_MODE_AUTO = [0x40, 0x00]
    COMMAND_MODE_MANUAL = [0x40, 0x40]

    COMMAND_SET_PROGRAM = [0x10]
    COMMAND_REQUEST_PROGRAM = [0x20]

    COMMAND_TEMPERATURE = [0x41]
    COMMAND_TEMPERATURE_ON = [0x41, 0x3c]
    COMMAND_TEMPERATURE_OFF = [0x41, 0x09]
    COMMAND_TEMPERATURE_COMFORT = [0x43]
    COMMAND_TEMPERATURE_ECO = [0x44]
    COMMAND_BOOST_START = [0x45, 0xff]
    COMMAND_BOOST_STOP = [0x45, 0x00]
    COMMAND_LOCK_ON = [0x80, 0x01]
    COMMAND_LOCK_OFF = [0x80, 0x00]
    COMMAND_COMFORT_ECO = [0x11]
    COMMAND_OFFSET = [0x13]
    COMMAND_OPEN_WINDOW = [0x14]
    COMMAND_RESET = [0xf0]

    NOTIFY_SERIAL = bytearray([0x01])
    NOTIFY_STATUS = bytearray([0x02, 0x01])
    NOTIFY_PROGRAM_CONFIRM = bytearray([0x02, 0x02])
    NOTIFY_PROGRAM_REQUEST = bytearray([0x21])

    def __init__(self, address: str) -> None:

        super().__init__(address, timeout=30.0)

        self.name: str = None
        self.vendor: str = None
        self.serialNumber: str = None
        self.firmware: float = None
        self.mode: Mode = None
        self.temperature: Temperature = None
        self.valve: int = None
        self.vacation: Vacation = None
        self.programs: list = [None] * 7
        self.ecoTemperature: Temperature = None
        self.comfortTemperature: Temperature = None
        self.openWindowConfig: OpenWindowConfig = None
        self.offsetTemperature: Temperature = None

    def onNotify(self, device, bytes):

        LOGGER.debug(f"<<< {device.address}: received notification("
                     f"{logManager.logger.hexstr(bytes)})")

        if bytes.startswith(Thermostat.NOTIFY_SERIAL):

            self.serialNumber = bytearray(
                [b - 0x30 for b in bytes[4:-1]]).decode()
            self.firmware = bytes[1] / 100
            LOGGER.debug(f"{device.address}: received serialNo and firmware version: "
                        f"{self.serialNumber}, {self.firmware}")

        elif bytes.startswith(Thermostat.NOTIFY_STATUS):

            self.mode = Mode(mode=bytes[2])
            self.valve = bytes[3]
            self.temperature = Temperature.fromByte(bytes[5])
            if len(bytes) > 9:
                self.vacation = Vacation.fromBytes(bytes[6:10])
            else:
                self.vacation = None

            if len(bytes) == 15:
                self.openWindowConfig = OpenWindowConfig.fromBytes(
                    bytes[10:12])
                self.comfortTemperature = Temperature.fromByte(bytes[12])
                self.ecoTemperature = Temperature.fromByte(bytes[13])
                self.offsetTemperature = Temperature.fromByte(bytes[14] - 7)
            else:
                self.openWindowConfig = None
                self.comfortTemperature = None
                self.ecoTemperature = None
                self.offsetTemperature = None
                LOGGER.debug(
                    f"{device.address}: outdated firmware detected.")

            LOGGER.debug(f"{device.address}: received status: mode={str(self.mode)}, temperature={str(self.temperature)}, valve={str(self.valve)}%, vacation={str(self.vacation)}, openWindowConfig="
                        f"{str(self.openWindowConfig)}, comfortTemperature={str(self.comfortTemperature)}, ecoTemperature={str(self.ecoTemperature)}, offsetTemperature={str(self.offsetTemperature)}")

        elif bytes.startswith(Thermostat.NOTIFY_PROGRAM_REQUEST):

            day = bytes[1]
            program = Program.fromBytes(bytes=bytes[2:])
            self.programs[day] = program
            LOGGER.debug(f"{device.address}: received program: "
                        f"{Program.DAYS[day]}={str(program)}")

        elif bytes.startswith(Thermostat.NOTIFY_PROGRAM_CONFIRM):

            LOGGER.debug(f"{device.address}: program for "
                        f"{Program.DAYS[bytes[2]]} has been successful")

    async def read_gatt_char(self, characteristic) -> bytearray:

        LOGGER.debug(">>> %s: read_gatt_char(%s)" %
                     (self.address, characteristic))
        response = await super().read_gatt_char(characteristic)

        if response:
            LOGGER.debug("<<< %s: %s" %
                         (self.address, logManager.logger.hexstr(response)))

        return response

    async def write_gatt_char(self, characteristic, data, response):

        LOGGER.debug(">>> %s: write_gatt_char(%s, %s)" %
                     (self.address, characteristic, logManager.logger.hexstr(data)))
        response = await super().write_gatt_char(characteristic, data=data, response=response)

        if response:
            LOGGER.debug("<<< %s: %s" %
                         (self.address, logManager.logger.hexstr(response)))

        return response

    async def connect(self):

        _self = self

        async def _notificationHandler(c, bytes: bytearray) -> None:

            _self.onNotify(device=_self, bytes=bytes)

        LOGGER.debug(f"{self.address}: connecting...")

        await super().connect()

        if self.is_connected:
            # Use the services property instead of get_services()
            services = self.services
            char = services.get_characteristic(Thermostat.CHARACTERISTIC_NOTIFICATION_HANDLE)
            if char and "notify" in char.properties:
                try:
                    await self.start_notify(
                        Thermostat.CHARACTERISTIC_NOTIFICATION_HANDLE, callback=_notificationHandler)
                    LOGGER.debug(f"{self.address}: successfully connected and notifications enabled")
                except Exception as e:
                    LOGGER.warning(f"{self.address}: failed to enable notifications for characteristic {Thermostat.CHARACTERISTIC_NOTIFICATION_HANDLE}: {e}")
                    LOGGER.debug(f"{self.address}: successfully connected (no notifications)")
            else:
                LOGGER.warning(f"{self.address}: notification not supported for characteristic {Thermostat.CHARACTERISTIC_NOTIFICATION_HANDLE}, skipping start_notify")
                LOGGER.debug(f"{self.address}: successfully connected (no notifications)")
        else:
            raise EqivaException(f"{self.address}: Connection failed")

    async def disconnect(self):

        LOGGER.debug(f"{self.address}: disconnecting...")
        await super().disconnect()
        LOGGER.debug(f"{self.address}: successfully disconnected")

    async def setTemperature(self, temperature: Temperature):

        LOGGER.info(f"{self.address}: set {str(temperature)}")
        bytes = list(Thermostat.COMMAND_TEMPERATURE)
        bytes.append(temperature.toByte())
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(bytes), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setTemperatureComfort(self):

        LOGGER.info(f"{self.address}: set mode to comfort")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_TEMPERATURE_COMFORT), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setTemperatureEco(self):

        LOGGER.info(f"{self.address}: set mode to ecor")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_TEMPERATURE_ECO), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setTemperatureOn(self):

        LOGGER.info(f"{self.address}: set thermostat on (30°C)")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_TEMPERATURE_ON), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setTemperatureOff(self):

        LOGGER.info(f"{self.address}: set thermostat off (4.5°C)")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_TEMPERATURE_OFF), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setModeAuto(self):

        LOGGER.info(f"{self.address}: set mode to auto")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_MODE_AUTO), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setModeManual(self):

        LOGGER.info(f"{self.address}: set mode to manual")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_MODE_MANUAL), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setBoost(self, on: bool):

        LOGGER.info(f"{self.address}: turn "
                    f"{'on' if on else 'off'} boost mode")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_BOOST_START if on else Thermostat.COMMAND_BOOST_STOP), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def requestStatus(self):

        LOGGER.debug(f"{self.address}: sync time and request status")
        now = datetime.now()
        bytes = list(Thermostat.COMMAND_STATUS)
        bytes.extend([now.year % 100, now.month, now.day,
                     now.hour, now.minute, now.second])
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(bytes), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setVacation(self, temperature: Temperature, vacation: Vacation):

        LOGGER.info(f"{self.address}: set "
                    f"{str(vacation)} with {str(temperature)}")
        bytes = list(Thermostat.COMMAND_VACATION)
        bytes.append(temperature.toByte() + 0x80)
        bytes.extend(vacation.toBytes())

        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(bytes), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def requestProgram(self, day: int):

        LOGGER.debug(f"{self.address}: request program for "
                    f"{str(Program.DAYS[day])}")

        requests = list()

        if day <= Program.DAY_FRIDAY:
            requests.append([Thermostat.COMMAND_REQUEST_PROGRAM[0], day])

        elif day == Program.DAY_WEEKEND:
            requests.extend([[Thermostat.COMMAND_REQUEST_PROGRAM[0], d]
                            for d in range(Program.DAY_SATURDAY, Program.DAY_SUNDAY + 1)])

        elif day == Program.DAY_WORKDAY:
            requests.extend([[Thermostat.COMMAND_REQUEST_PROGRAM[0], d]
                            for d in range(Program.DAY_MONDAY, Program.DAY_FRIDAY + 1)])

        elif day == Program.DAY_EVERYDAY:
            requests.extend([[Thermostat.COMMAND_REQUEST_PROGRAM[0], d]
                            for d in range(Program.DAY_SATURDAY, Program.DAY_FRIDAY + 1)])

        elif day == Program.DAY_TODAY:
            requests.append([Thermostat.COMMAND_REQUEST_PROGRAM[0],
                            (datetime.now().weekday() + 2) % 7])

        elif day == Program.DAY_TOMORROW:
            requests.append([Thermostat.COMMAND_REQUEST_PROGRAM[0],
                            (datetime.now().weekday() + 3) % 7])

        for r in requests:
            await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(r), response=True)

        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setProgram(self, day: int, program: Program) -> 'list[Thermostat]':

        LOGGER.info(f"{self.address}: set "
                    f"{str(program)} on {Program.DAYS[day]}")

        bytes = list(Thermostat.COMMAND_SET_PROGRAM)

        if day == Program.DAY_TODAY:
            day = (datetime.now().weekday() + 2) % 7
        elif day == Program.DAY_TOMORROW:
            day = (datetime.now().weekday() + 3) % 7
        bytes.append(day)

        bytes.extend(program.toBytes())

        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(bytes), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setOffsetTemperature(self, offset: Temperature):

        LOGGER.info(f"{self.address}: set offset {str(offset)}")
        bytes = list(Thermostat.COMMAND_OFFSET)
        bytes.append(offset.toByte() + 7)
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(bytes), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setComfortEcoTemperature(self, comfort: Temperature, eco: Temperature):

        LOGGER.info(f"{self.address}: set comfort to "
                    f"{str(comfort)} and eco to {str(eco)}")
        bytes = list(Thermostat.COMMAND_COMFORT_ECO)
        bytes.append(comfort.toByte())
        bytes.append(eco.toByte())
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(bytes), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setOpenWindow(self, openWindowConfig: OpenWindowConfig):

        LOGGER.info(f"{self.address}: set open window to "
                    f"{str(openWindowConfig)}")
        bytes = list(Thermostat.COMMAND_OPEN_WINDOW)
        bytes.extend(openWindowConfig.toBytes())
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(bytes), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def setLock(self, on: bool):

        LOGGER.info(f"{self.address}: turn {'on' if on else 'off'} lock")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_LOCK_ON if on else Thermostat.COMMAND_LOCK_OFF), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def reset(self):

        LOGGER.info(f"{self.address}: perform factory reset")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_RESET), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def requestSerialNo(self) -> None:

        LOGGER.info(f"{self.address}: request serialno")
        await self.write_gatt_char(Thermostat.CHARACTERISTIC_REQUEST_HANDLE, bytearray(Thermostat.COMMAND_SERIAL), response=True)
        await asyncio.sleep(Thermostat.WAIT_NOTIFICATION)

    async def requestName(self) -> str:

        LOGGER.info(f"{self.address}: request name")
        name = await self.read_gatt_char(Thermostat.CHARACTERISTIC_DEVICE_NAME_STRING)
        self.name = name.decode()
        LOGGER.info(f"{self.address}: name is {self.name}")
        return self.name

    async def requestVendor(self) -> str:

        LOGGER.info(f"{self.address}: request vendor")
        vendor = await self.read_gatt_char(Thermostat.CHARACTERISTIC_VENDOR_STRING)
        self.vendor = vendor.decode()
        LOGGER.info(f"{self.address}: name is {self.vendor}")
        return self.vendor

    def to_dict(self) -> dict:

        return {
            "mac": self.address,
            "name": self.name,
            "vendor": self.vendor,
            "serialNumber": self.serialNumber,
            "firmware": self.firmware,
            "mode": self.mode.to_dict() if self.mode else None,
            "temperature": self.temperature.to_dict() if self.temperature else None,
            "valve": self.valve,
            "vacation": self.vacation.to_dict() if self.vacation else None,
            "program": {Program.DAYS[d]: p.to_dict() for d, p in enumerate(self.programs) if p},
            "ecoTemperature": self.ecoTemperature.to_dict() if self.ecoTemperature else None,
            "comfortTemperature": self.comfortTemperature.to_dict() if self.comfortTemperature else None,
            "openWindowConfig": self.openWindowConfig.to_dict() if self.openWindowConfig else None,
            "offsetTemperature": self.offsetTemperature.to_dict() if self.offsetTemperature else None
        }

    def __str__(self) -> str:

        programs = ", ".join(
            [f"{Program.DAYS[d]}={str(p)}" for d, p in enumerate(self.programs) if p])
        return f"Thermostat(address={self.address}, name={self.name}, vendor={self.vendor}, serialNo={self.serialNumber}, firmware={self.firmware}, mode={str(self.mode)}, temperature={str(self.temperature)}, valve={str(self.valve)}%, vacation={str(self.vacation)}, programs=Programs({programs}), openWindowConfig={str(self.openWindowConfig)}, comfortTemperature={str(self.comfortTemperature)}, ecoTemperature={str(self.ecoTemperature)}, offsetTemperature={str(self.offsetTemperature)})"
