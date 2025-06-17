import asyncio
import json
import re
import sys
from datetime import datetime, timedelta

from bleak import BleakError
#from bleak.backends.device import BLEDevice
from bleak.backends.scanner import BLEDevice

from MyLogger import MyLogger
from EqivaException import EqivaException
from Temperature import Temperature
from Event import Event
from Program import Program
from Vacation import Vacation
from OpenWindowConfig import OpenWindowConfig
from Mode import Mode
from Listener import Listener
from Thermostat import Thermostat
from Alias import Alias
from ThermostatController import ThermostatController

_MAX_BLE_CONNECTIONS = 8

LOGGER = MyLogger()

global use_bdaddr

class ThermostatCLI():

    _USAGE = "usage"
    _DESCR = "descr"
    _REGEX = "regex"
    _TYPES = "types"

    _COMMAND = "command"
    _ARGS = "args"
    _PARAMS = "params"

    COMMANDS = {
        "temp": {
            _USAGE: "--temp <temp>",
            _DESCR: "set temperature from 4.5 to 30.0°C in steps of 0.5°C or one of 'comfort', 'eco', 'off', 'on'",
            _REGEX: r"^(on|off|comfort|eco|4\.5|[5-9]\.[05]|[12][0-9]\.[05]|30\.0)$",
            _TYPES: [str]
        },
        "mode": {
            _USAGE: "--mode <auto|manual>",
            _DESCR: "set mode to auto or manual",
            _REGEX: r"^(auto|manual)$",
            _TYPES: [str]
        },
        "boost": {
            _USAGE: "--boost <on|off>",
            _DESCR: "start or stop boost",
            _REGEX: r"^(on|off)?$",
            _TYPES: [str]
        },
        "status": {
            _USAGE: "--status",
            _DESCR: "synchronize time and get status information",
            _REGEX: None,
            _TYPES: None
        },
        "vacation": {
            _USAGE: "--vacation <YYYY-MM-DD hh:mm|hh:mm|hh> <temp>",
            _DESCR: "set temperature for period, e.g. specific time, for hours and minutes from now on, for hours",
            _REGEX: r"^(20\d{2}\-\d{2}\-\d{2} (2[0-3]|[01]?[0-9]):[30]0|\d{1,2}:[0-5]\d|\d+) (4\.5|[5-9]\.[05]|[12][0-9]\.[05]|30\.0)$",
            _TYPES: [str] * 3
        },
        "program": {
            _USAGE: "--program [<day>] [<temp>] [<hh:mm> <temp>] ...",
            _DESCR: "request all programs, programs of a weekday OR set program with max. 7 events.\n<day> must be one of 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'weekend', 'work', 'everyday', 'today', 'tomorrow'\ntime must be in stepts of 10 minutes",
            _REGEX: r"^(mon|tue|wed|thu|fri|sat|sun|weekend|work|everyday|today|tomorrow)?( (4\.5|[5-9]\.[05]|[12][0-9]\.[05]|30\.0)( [01]?\d| 2[0-3]):([0-5]0)){0,7}( (4\.5|[5-9]\.[05]|[12][0-9]\.[05]|30\.0))?$",
            _TYPES: [str] * 14
        },
        "offset": {
            _USAGE: "--offset <temp>",
            _DESCR: "set offset temperature from -3.5 to 3.5°C in steps of 0.5°C",
            _REGEX: r"^-?[0-3]\.[05]$",
            _TYPES: [float]
        },
        "comforteco": {
            _USAGE: "--comforteco <temp> <temp>",
            _DESCR: "set comfort and eco temperature from 4.5 to 30.0°C in steps of 0.5°C",
            _REGEX: r"^(4\.5|[5-9]\.[05]|[12][0-9]\.[05]|30\.0) (4\.5|[5-9]\.[05]|[12][0-9]\.[05]|30\.0)$",
            _TYPES: [float] * 2
        },
        "openwindow": {
            _USAGE: "--openwindow <temp> <minutes>",
            _DESCR: "set temperature (4.5 to 30.0) and minutes (in steps of 5min, max. 995min) after open windows has been detected",
            _REGEX: r"^(4\.5|[5-9]\.[05]|[12][0-9]\.[05]|30\.0) (\d{0,2}[05])$",
            _TYPES: [float, int]
        },
        "lock": {
            _USAGE: "--lock <on|off>",
            _DESCR: "lock or unlock thermostat",
            _REGEX: r"^(on|off)?$",
            _TYPES: [str]
        },
        "scan": {
            _USAGE: "--scan",
            _DESCR: "scan for Eqiva Smart Radiotor Thermostats",
            _REGEX: None,
            _TYPES: None
        },
        "aliases": {
            _USAGE: "--aliases",
            _DESCR: "print known aliases from .known_eqivas file",
            _REGEX: None,
            _TYPES: None
        },
        "reset": {
            _USAGE: "--reset",
            _DESCR: "perform factory reset",
            _REGEX: None,
            _TYPES: None
        },
        "serial": {
            _USAGE: "--serial",
            _DESCR: "request serialNo of thermostat and firmware version",
            _REGEX: None,
            _TYPES: None
        },
        "name": {
            _USAGE: "--name",
            _DESCR: "request device name of thermostat",
            _REGEX: None,
            _TYPES: None
        },
        "vendor": {
            _USAGE: "--vendor",
            _DESCR: "request vendor of thermostat",
            _REGEX: None,
            _TYPES: None
        },
        "dump": {
            _USAGE: "--dump",
            _DESCR: "request full state of thermostat",
            _REGEX: None,
            _TYPES: None
        },
        "print": {
            _USAGE: "--print",
            _DESCR: "prints collected data of thermostat",
            _REGEX: None,
            _TYPES: None
        },
        "commands": {
            _USAGE: "--commands",
            _DESCR: "prints collected data of thermostat in command style for easy re-use",
            _REGEX: None,
            _TYPES: None
        },
        "json": {
            _USAGE: "--json",
            _DESCR: "prints information in json format",
            _REGEX: None,
            _TYPES: None
        },
        "log": {
            _USAGE: "--log <DEBUG|INFO|WARN|ERROR>",
            _DESCR: "set loglevel",
            _REGEX: r"^(DEBUG|INFO|WARN|ERROR)$",
            _TYPES: [str]
        },
        "help": {
            _USAGE: "--help [<command>]",
            _DESCR: "prints help optionally for given command",
            _REGEX: r"^([a-z-]+)?$",
            _TYPES: None
        },
        "macos-use-bdaddr": {
            _USAGE: "--macos-use-bdaddr",
            _DESCR: "use bluetooth device address instead of mac address",
            _REGEX: None,
            _TYPES: None
        }
    }

    def __init__(self, argv: 'list[str]') -> None:

        global use_bdaddr
        self.alias: Alias = Alias()
        try:

            argv.pop(0)
            if "--log" in sys.argv:
                MyLogger.level = MyLogger.LEVELS[sys.argv[sys.argv.index("--log") + 1]]
                LOGGER.level = MyLogger.level
                
            if "--macos-use-bdaddr" in sys.argv:
                ThermostatController.use_bdaddr = True
                LOGGER.info("Using bdaddr for macOS")

            if argv and (argv[0] == "--help" or argv[0] == "-h"):
                if len(argv) == 2:
                    print(self._build_help(
                        command=argv[1], header=True), file=sys.stderr, flush=True)
                else:
                    self.print_help()

            elif argv and argv[0] == "--scan":
                self.scan()

            elif argv and argv[0] == "--aliases":
                print(str(self.alias), flush=True)

            else:
                addresses, commands = self.parse_args(sys.argv)
                if addresses and len(addresses) > _MAX_BLE_CONNECTIONS:
                    raise EqivaException(message="Too many simultaneous connections requested, i.e. max. %i but requested %i" % (
                        _MAX_BLE_CONNECTIONS, len(addresses)))
                elif addresses and commands:
                    asyncio.run(self.process(
                        addresses=addresses, commands=commands))
                elif not addresses:
                    raise EqivaException(
                        message="Mac address or alias unknown")

        except EqivaException as e:
            LOGGER.error(e.message)

        except TimeoutError:
            LOGGER.error(
                f"TimeoutError! Maybe too many connections simultaneously?")

        except KeyboardInterrupt:
            pass

    def _build_help(self, command=None, header=False, msg="") -> None:

        s = ""

        if header == True:
            s = """Eqiva Smart Radiator Thermostat command line interface for Linux / Raspberry Pi / Windows

USAGE:   eqiva.py <mac_1/alias_1> [<mac_2/alias_2>] ... --<command_1> [<param_1> <param_2> ... --<command_2> ...]
         <mac_N>   : bluetooth mac address of thermostat
         <alias_N> : you can use aliases instead of mac address if there is a ~/.known_eqiva file
         <command> : a list of commands and parameters
         """

        if msg != "":
            s += "\n " + msg

        if command is not None and command in ThermostatCLI.COMMANDS:
            s += "\n " + \
                ThermostatCLI.COMMANDS[command][ThermostatCLI._USAGE].ljust(32)
            for i, d in enumerate(ThermostatCLI.COMMANDS[command][ThermostatCLI._DESCR].split("\n")):
                s += ("\n " + (" " * 32) + d if i > 0 or len(ThermostatCLI.COMMANDS[command]
                                                             [ThermostatCLI._USAGE]) >= 32 else d)

        if msg != "":
            s += "\n"

        return s

    def scan(self):

        class ScanListener(Listener):

            def __init__(self) -> None:
                self._seen: 'set[BLEDevice]' = set()

            def onScanSeen(self, device: BLEDevice) -> None:
                self._seen.add(device)
                print(' %i bluetooth devices seen' %
                      len(self._seen), end='\r', file=sys.stderr, flush=True)

            def onScanFound(self, device: BLEDevice) -> None:
                print(f"{device.address}     {device.name}", flush=True)

        print("MAC-Address           Thermostat name", flush=True)
        asyncio.run(ThermostatController.scan(listener=ScanListener()))

    def print_help(self):

        help = self._build_help(header=True)

        help += "\nBasic commands:"
        help += self._build_help(command="temp")
        help += self._build_help(command="mode")
        help += self._build_help(command="boost")
        help += self._build_help(command="vacation")
        help += self._build_help(command="status")

        help += "\n\nConfiguration commands:"
        help += self._build_help(command="program")
        help += self._build_help(command="offset")
        help += self._build_help(command="comforteco")
        help += self._build_help(command="openwindow")
        help += self._build_help(command="lock")

        help += "\n\nSetup commands:"
        help += self._build_help(command="scan")
        help += self._build_help(command="aliases")
        help += self._build_help(command="reset")

        help += "\n\nOther commands:"
        help += self._build_help(command="serial")
        help += self._build_help(command="name")
        help += self._build_help(command="vendor")
        help += self._build_help(command="dump")
        help += self._build_help(command="print")
        help += self._build_help(command="commands")
        help += self._build_help(command="json")
        help += self._build_help(command="log")
        help += self._build_help(command="help")

        help += "\n"
        print(help, file=sys.stderr, flush=True)

    def to_human_readable(self, controller: ThermostatController, command_style: bool = False) -> str:

        def mode_to_human_readable(mode: Mode) -> str:

            modes = mode.to_dict()
            if command_style:
                s = list()
                if Mode.MODES[0] in modes:
                    s.append(" --mode auto")
                elif Mode.MODES[1] in modes:
                    s.append(" --mode manual")
                s.append(" --boost %s" %
                         ("on" if Mode.MODES[3] in modes else "off"))
                s.append(" --lock %s" %
                         ("on" if Mode.MODES[6] in modes else "off"))
                return "\n".join(s)
            else:
                return ", ".join([m.lower().replace("_", " ") for m in modes])

        def temp_to_human_readable(temp: Temperature) -> str:

            if not temp:
                return "n/a"

            if command_style:
                return f"{temp.valueC:.1f}"

            else:
                return f"{temp.valueC:.1f}°C ({temp.fahrenheit():.1f}°F)"

        def vacation_to_human_readable(vacation: Vacation, temperature: Temperature) -> str:

            if vacation and vacation.until:
                if command_style:
                    return "%s %s" % (vacation.until.strftime("%Y-%m-%d %H:%M"), temp_to_human_readable(temperature))
                else:
                    return "%s until %s" % (temp_to_human_readable(temperature), vacation.until.strftime("%Y-%m-%d %H:%M"))
            else:
                return "" if command_style else "off"

        def openwindow_to_human_readable(openwindowconfig: OpenWindowConfig) -> str:

            if not openwindowconfig:
                return "n/a"

            if command_style:
                return f"{temp_to_human_readable(openwindowconfig.temperature)} {openwindowconfig.minutes}"
            else:
                return f"{temp_to_human_readable(openwindowconfig.temperature)} for {openwindowconfig.minutes} minutes"

        def event_to_human_readable(event: Event) -> str:

            if command_style and event.hour == 24:
                return f"{temp_to_human_readable(event.temperature)}"
            elif command_style:
                return f"{temp_to_human_readable(event.temperature)} {event.hour:02}:{event.minute:02}"
            else:
                return f"{temp_to_human_readable(event.temperature)} until {event.hour:02}:{event.minute:02}"

        def program_to_human_readable(program: Program) -> str:

            if command_style:
                return " ".join([event_to_human_readable(event=e) for e in program.events if e.hour != 0])
            else:
                return "\n".join(["    %s" % event_to_human_readable(event=e) for e in program.events if e.hour != 0])

        def thermostat_to_human_readable(thermostat: Thermostat) -> str:

            s = list()
            s.append("")
            s.append("Thermostat %s" % thermostat.address)
            if thermostat.name and not command_style:
                s.append("  Name:                %s" % thermostat.name)

            if thermostat.vendor and not command_style:
                s.append("  Vendor:              %s" % thermostat.vendor)

            if thermostat.serialNumber and not command_style:
                s.append("  Serial no.:          %s" % thermostat.serialNumber)
                s.append("  Firmware:            %s" % thermostat.firmware)

            if thermostat.mode and not command_style:
                s.append("  Modes:               %s" %
                         mode_to_human_readable(thermostat.mode))
                s.append("  Temperature:         %s" %
                         temp_to_human_readable(thermostat.temperature))
                s.append("  Vacation:            %s" % vacation_to_human_readable(
                    thermostat.vacation, temperature=thermostat.temperature))
                s.append("  Valve:               %s" %
                         (f"{thermostat.valve}%"))
                s.append("")
                s.append("  Comfort temperature: %s" %
                         temp_to_human_readable(thermostat.comfortTemperature))
                s.append("  Eco temperature:     %s" %
                         temp_to_human_readable(thermostat.ecoTemperature))
                s.append("  Open window mode:    %s" %
                         openwindow_to_human_readable(thermostat.openWindowConfig))
                s.append("  Offset temperature:  %s" %
                         temp_to_human_readable(thermostat.offsetTemperature))
                s.append("")
            elif thermostat.mode:
                s.append(mode_to_human_readable(thermostat.mode))
                s.append(" --temp %s" %
                         temp_to_human_readable(thermostat.temperature))
                if thermostat.vacation.until:
                    s.append(" --vacation %s" % vacation_to_human_readable(
                        thermostat.vacation, temperature=thermostat.temperature))
                s.append(" --comforteco %s %s" % (
                    temp_to_human_readable(thermostat.comfortTemperature),
                    temp_to_human_readable(thermostat.ecoTemperature)))
                s.append(" --openwindow %s" %
                         openwindow_to_human_readable(thermostat.openWindowConfig))
                s.append(" --offset %s" %
                         temp_to_human_readable(thermostat.offsetTemperature))

            if command_style:
                s.extend([" --program %s %s" % (Program.DAYS[(d + 2) % 7], program_to_human_readable(thermostat.programs[(d + 2) %
                                                                                                                         7])) for d in range(7) if thermostat.programs[(d + 2) % 7]])
            else:
                s.extend(["  Program on %s:\n%s\n" % (Program.DAYS_LONG[(d + 2) % 7], program_to_human_readable(thermostat.programs[(d + 2) %
                                                                                                                                    7])) for d in range(7) if thermostat.programs[(d + 2) % 7]])

            return "\n".join(s)

        return "\n\n".join([thermostat_to_human_readable(thermostat=t) for t in controller.thermostats])

    async def process(self, addresses: 'list[str]', commands: 'list[dict]') -> None:

        try:
            controller = ThermostatController(addresses=addresses)

            await controller.connect(timeout=15)

            for command in commands:
                if command[ThermostatCLI._COMMAND] == "temp":

                    if command[ThermostatCLI._PARAMS][0] == "comfort":
                        await asyncio.gather(controller.setTemperatureComfort())

                    elif command[ThermostatCLI._PARAMS][0] == "eco":
                        await asyncio.gather(controller.setTemperatureEco())

                    elif command[ThermostatCLI._PARAMS][0] == "on":
                        await asyncio.gather(controller.setTemperatureOn())

                    elif command[ThermostatCLI._PARAMS][0] == "off":
                        await asyncio.gather(controller.setTemperatureOff())

                    else:
                        await asyncio.gather(controller.setTemperature(temperature=Temperature(valueC=float(command[ThermostatCLI._PARAMS][0]))))

                elif command[ThermostatCLI._COMMAND] == "mode":

                    if command[ThermostatCLI._PARAMS][0] == "auto":
                        await asyncio.gather(controller.setModeAuto())

                    elif command[ThermostatCLI._PARAMS][0] == "manual":
                        await asyncio.gather(controller.setModeManual())

                elif command[ThermostatCLI._COMMAND] == "boost":

                    if not command[ThermostatCLI._PARAMS] or command[ThermostatCLI._PARAMS][0] == "on":
                        await asyncio.gather(controller.setBoost(on=True))

                    elif command[ThermostatCLI._PARAMS][0] == "off":
                        await asyncio.gather(controller.setBoost(on=False))

                elif command[ThermostatCLI._COMMAND] == "status":
                    await asyncio.gather(controller.requestStatus())

                elif command[ThermostatCLI._COMMAND] == "vacation":
                    if len(command[ThermostatCLI._PARAMS]) == 3:
                        temp = Temperature(valueC=float(
                            command[ThermostatCLI._PARAMS][2]))
                        datetime_ = datetime.strptime(
                            " ".join(command[ThermostatCLI._PARAMS][:2]), "%Y-%m-%d %H:%M")
                        await asyncio.gather(controller.setVacation(temperature=temp, datetime_=datetime_))

                    elif len(command[ThermostatCLI._PARAMS]) == 2:

                        if ":" in command[ThermostatCLI._PARAMS][0]:
                            temp = Temperature(valueC=float(
                                command[ThermostatCLI._PARAMS][1]))
                            hhmm = command[ThermostatCLI._PARAMS][0].split(":")
                            await asyncio.gather(
                                controller.setVacation(
                                    temperature=temp,
                                    time_=timedelta(hours=int(hhmm[0]), minutes=int(hhmm[1]))))

                        else:
                            temp = Temperature(valueC=float(
                                command[ThermostatCLI._PARAMS][1]))
                            hours = int(command[ThermostatCLI._PARAMS][0])
                            await asyncio.gather(
                                controller.setVacation(
                                    temperature=temp,
                                    hours=hours))

                elif command[ThermostatCLI._COMMAND] == "program":

                    if len(command[ThermostatCLI._PARAMS]) == 0:

                        await asyncio.gather(controller.requestProgram(day=Program.DAY_EVERYDAY))

                    elif len(command[ThermostatCLI._PARAMS]) == 1:

                        await asyncio.gather(controller.requestProgram(day=Program.DAYS.index(command[ThermostatCLI._PARAMS][0])))

                    else:
                        events: 'list[Event]' = list()
                        temp = None
                        for i, param in enumerate(command[ThermostatCLI._PARAMS][1:]):
                            if i % 2:
                                hour, minute = tuple(param.split(":"))
                                events.append(
                                    Event(temperature=temp, hour=int(hour), minute=int(minute)))
                            else:
                                temp = Temperature(valueC=float(param))

                        events.append(
                            Event(temperature=events[0].temperature if i % 2 else temp, hour=24, minute=0))

                        await asyncio.gather(controller.setProgram(day=Program.DAYS.index(command[ThermostatCLI._PARAMS][0]), program=Program(events=events)))

                elif command[ThermostatCLI._COMMAND] == "offset":

                    await asyncio.gather(controller.setOffsetTemperature(offset=Temperature(valueC=command[ThermostatCLI._PARAMS][0])))

                elif command[ThermostatCLI._COMMAND] == "comforteco":

                    await asyncio.gather(controller.setComfortEcoTemperature(comfort=Temperature(valueC=command[ThermostatCLI._PARAMS][0]), eco=Temperature(valueC=command[ThermostatCLI._PARAMS][1])))

                elif command[ThermostatCLI._COMMAND] == "openwindow":

                    openWindowConfig = OpenWindowConfig(temperature=Temperature(
                        valueC=command[ThermostatCLI._PARAMS][0]), minutes=command[ThermostatCLI._PARAMS][1])
                    await asyncio.gather(controller.setOpenWindow(openWindowConfig=openWindowConfig))

                elif command[ThermostatCLI._COMMAND] == "lock":

                    if not command[ThermostatCLI._PARAMS] or command[ThermostatCLI._PARAMS][0] == "on":
                        await asyncio.gather(controller.setLock(on=True))

                    elif command[ThermostatCLI._PARAMS][0] == "off":
                        await asyncio.gather(controller.setLock(on=False))

                elif command[ThermostatCLI._COMMAND] == "reset":

                    await asyncio.gather(controller.reset())

                elif command[ThermostatCLI._COMMAND] == "serial":
                    await asyncio.gather(controller.requestSerialNo())

                elif command[ThermostatCLI._COMMAND] == "name":
                    await asyncio.gather(controller.requestName())

                elif command[ThermostatCLI._COMMAND] == "vendor":
                    await asyncio.gather(controller.requestVendor())

                elif command[ThermostatCLI._COMMAND] == "dump":
                    await asyncio.gather(controller.requestDeviceInfo())

                elif command[ThermostatCLI._COMMAND] == "print":
                    print(self.to_human_readable(
                        controller=controller), flush=True)

                elif command[ThermostatCLI._COMMAND] == "commands":
                    print(self.to_human_readable(
                        controller=controller, command_style=True), flush=True)

                elif command[ThermostatCLI._COMMAND] == "json":
                    print(json.dumps(controller.to_dict(), indent=2), flush=True)

        except EqivaException as ex:
            LOGGER.error(ex.message)

        except BleakError as ex:
            LOGGER.error(str(ex))

        finally:
            if controller:
                await controller.disconnect()

    def transform_commands(self, commands: 'list[dict]'):

        errors: 'list[str]' = list()

        for command in commands:

            cmd = command[ThermostatCLI._COMMAND]
            if cmd not in ThermostatCLI.COMMANDS:
                errors.append("ERROR: Unknown command <%s>" % cmd)
                continue

            cmd_def = ThermostatCLI.COMMANDS[cmd]

            regex: str = cmd_def[ThermostatCLI._REGEX]
            if regex and not re.match(regex, " ".join(command[ThermostatCLI._ARGS])):
                errors.append(
                    self._build_help(cmd, False,
                                     "ERROR: Please check parameters of command\n")
                )
                continue

            if cmd_def[ThermostatCLI._TYPES]:
                params = []
                for i, arg in enumerate(command[ThermostatCLI._ARGS]):
                    params.append(cmd_def[ThermostatCLI._TYPES][i](arg))

                command["params"] = params

        if len(commands) == 0:
            errors.append(
                "No commands given. Use --help in order to get help")

        if len(errors) > 0:
            raise EqivaException("\n".join(errors))

        return commands

    def parse_args(self, argv: 'list[str]') -> 'tuple[set[str], list[dict]]':

        addresses: 'set[str]' = set()
        commands: 'list[tuple[str, list[str]]]' = list()

        cmd_group = False
        for arg in argv:

            is_cmd = arg.startswith("--")
            cmd_group |= is_cmd
            if not cmd_group:
                _addresses = self.alias.resolve(arg)
                if _addresses:
                    for a in _addresses:
                        addresses.add(a)
                else:
                    addresses.add(arg)

            elif is_cmd:
                commands.append({
                    "command": arg[2:],
                    "args": list()
                })

            else:
                commands[-1]["args"].append(arg)

        self.transform_commands(commands)

        return addresses, commands
