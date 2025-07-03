import asyncio
import time
from datetime import datetime, timedelta

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from utils.Thermostat import Thermostat
from utils.Listener import Listener
from utils.Program import Program
from utils.Temperature import Temperature
from utils.Vacation import Vacation
from utils.OpenWindowConfig import OpenWindowConfig
from utils.EqivaException import EqivaException

import logManager

LOGGER = logManager.logger.get_logger(__name__)

class ThermostatController():

    use_bdaddr = False

    def __init__(self, addresses: 'list[str]') -> None:

        self.addresses: 'list[str]' = addresses
        self.thermostats: 'list' = list()

    async def connect(self, timeout) -> None:

        LOGGER.info("Request to connect to %s" % ", ".join(self.addresses))
        devices = await ThermostatController.scan(duration=timeout + len(self.addresses), filter_=self.addresses)
        LOGGER.debug("Found devices are %s" % (
            ", ".join([f"{d.name} ({d.address})" for d in devices]) if devices else "n/a"))

        if len(devices) < len(self.addresses):
            raise EqivaException(
                message="Could not find all given addresses")
        else:
            self.thermostats = [Thermostat(device) for device in devices]

        coros = [thermostat.connect() for thermostat in self.thermostats]
        await asyncio.gather(*coros)

    async def disconnect(self) -> None:

        coros = [thermostat.disconnect()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)

    async def setTemperature(self, temperature: Temperature) -> 'list':

        coros = [thermostat.setTemperature(temperature=temperature)
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setTemperatureComfort(self) -> 'list':

        coros = [thermostat.setTemperatureComfort()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setTemperatureEco(self) -> 'list':

        coros = [thermostat.setTemperatureEco()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setTemperatureOn(self) -> 'list':

        coros = [thermostat.setTemperatureOn()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setTemperatureOff(self) -> 'list':

        coros = [thermostat.setTemperatureOff()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setModeAuto(self) -> 'list':

        coros = [thermostat.setModeAuto()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setModeManual(self) -> 'list':

        coros = [thermostat.setModeManual()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setBoost(self, on: bool) -> 'list':

        coros = [thermostat.setBoost(on=on)
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def requestStatus(self) -> 'list':

        coros = [thermostat.requestStatus()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setVacation(self, temperature: Temperature, datetime_: datetime = None, time_: timedelta = None, hours: int = 0) -> 'list':

        if datetime_:
            vacation = Vacation(until=datetime_)
        elif time_:
            vacation = Vacation(until=datetime.now() + time_)
        else:
            vacation = Vacation(until=datetime.now() + timedelta(hours=hours))

        coros = [thermostat.setVacation(temperature=temperature, vacation=vacation)
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def requestProgram(self, day: int) -> 'list':

        coros = [thermostat.requestProgram(day=day)
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setProgram(self, day: int, program: Program) -> 'list':

        coros = [thermostat.setProgram(day=day, program=program)
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setOffsetTemperature(self, offset: Temperature) -> 'list':

        coros = [thermostat.setOffsetTemperature(offset=offset)
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setComfortEcoTemperature(self, comfort: Temperature, eco: Temperature) -> 'list':

        coros = [thermostat.setComfortEcoTemperature(comfort=comfort, eco=eco)
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setOpenWindow(self, openWindowConfig: OpenWindowConfig) -> 'list':

        coros = [thermostat.setOpenWindow(openWindowConfig=openWindowConfig)
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def setLock(self, on: bool) -> 'list':

        coros = [thermostat.setLock(on=on)
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def reset(self) -> None:

        coros = [thermostat.reset()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def requestSerialNo(self) -> 'list':

        coros = [thermostat.requestSerialNo()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def requestName(self) -> 'list':

        coros = [thermostat.requestName()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def requestVendor(self) -> 'list':

        coros = [thermostat.requestVendor()
                 for thermostat in self.thermostats if thermostat.is_connected]
        await asyncio.gather(*coros)
        return self.thermostats

    async def requestDeviceInfo(self) -> 'list':

        for thermostat in self.thermostats:
            await thermostat.requestName()
            await thermostat.requestVendor()
            await thermostat.requestSerialNo()
            await thermostat.requestStatus()
            await thermostat.requestProgram(Program.DAY_EVERYDAY)

        return self.thermostats

    def to_dict(self) -> dict:

        return [t.to_dict() for t in self.thermostats]

    @staticmethod
    async def scan(duration: int = 20, filter_: 'list[str]' = None, listener: 'Listener' = None) -> 'set[BLEDevice]':

        found_devices: 'set[BLEDevice]' = set()
        found_bulbs: 'set[BLEDevice]' = set()
        if filter_:
            consumed_filter = [m for m in filter_]
        else:
            consumed_filter = None

        def callback(device: BLEDevice, advertising_data: AdvertisementData):

            if device not in found_devices and device.name:
                found_devices.add(device)
                if device.address.upper().startswith(Thermostat.MAC_PREFIX):

                    if consumed_filter and device.address not in found_bulbs:
                        if device.address in consumed_filter or device.name in consumed_filter:
                            found_bulbs.add(device)
                            consumed_filter.remove(
                                device.address if device.address in consumed_filter else device.name)
                            if listener:
                                listener.onScanFound(device)

                    elif not filter_:
                        found_bulbs.add(device)
                        if listener:
                            listener.onScanFound(device)

            if listener:
                listener.onScanSeen(device)

        scanner_kwargs = {}
        if ThermostatController.use_bdaddr:
            scanner_kwargs["cb"] = {"use_bdaddr": ThermostatController.use_bdaddr}

        async with BleakScanner(callback, **scanner_kwargs) as scanner:
            if consumed_filter:
                start_time = time.time()
                while consumed_filter and (start_time + duration) > time.time():
                    await asyncio.sleep(.1)
            elif duration:
                await asyncio.sleep(duration)
            else:
                while True:
                    await asyncio.sleep(1)

        return found_bulbs
