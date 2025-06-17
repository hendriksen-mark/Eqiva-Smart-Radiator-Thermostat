import os
import re
from utils.Thermostat import Thermostat
from utils.MyLogger import MyLogger

LOGGER = MyLogger()

class Alias():

    _KNOWN_DEVICES_FILE = ".known_eqivas"
    MAC_PATTERN = r"^([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2})$"

    def __init__(self) -> None:

        self.aliases: 'dict[str,str]' = dict()
        try:
            filename = os.path.join(os.environ['USERPROFILE'] if os.name == "nt" else os.environ['HOME']
                                    if "HOME" in os.environ else "~", Alias._KNOWN_DEVICES_FILE)

            if os.path.isfile(filename):
                with open(filename, "r") as ins:
                    for line in ins:
                        # Remove comments marked with #
                        line = re.sub(r"\s*#.*", "", line)
                        _m = re.match(
                            r"([0-9A-Fa-f:]+)\s+(.*)$", line)
                        if _m and (_m.groups()[0].upper().startswith(Thermostat.MAC_PREFIX) or _m.groups()[0].upper().endswith(Thermostat.MAC_PREFIX)):
                            self.aliases[_m.groups()[0]] = _m.groups()[1]

        except:
            pass

    def resolve(self, label: str) -> 'set[str]':

        if re.match(Alias.MAC_PATTERN, label.upper()):
            label = label.upper()
            if label.upper().startswith(Thermostat.MAC_PREFIX) or label.upper().endswith(Thermostat.MAC_PREFIX):
                return [label]
            else:
                return None
        else:
            macs = {a.upper()
                    for a in self.aliases if label in self.aliases[a]}
            if macs:
                LOGGER.debug("Found mac-addresses for aliases: %s" %
                             ", ".join(macs))
            else:
                LOGGER.debug("No aliases found")

            return macs if macs else None

    def __str__(self) -> str:

        return "\n".join([f"{a}\t{self.aliases[a]}" for a in self.aliases])
