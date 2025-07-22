from .Temperature import Temperature
from .EqivaException import EqivaException

class Event():

    def __init__(self, temperature: Temperature = None, hour: int = 0, minute: int = 0):

        if hour < 0 or hour > 24 or minute < 0 or minute > 50 or minute % 10 != 0:
            raise EqivaException(
                'hour must be between 0 and 24. minute must be between 0 and 50 in steps of 10')

        self.hour = hour
        self.minute = minute
        self.temperature: Temperature = temperature

    @staticmethod
    def fromBytes(bytes: bytearray) -> 'Event':

        temperature = Temperature.fromByte(bytes[0])
        hour = bytes[1] // 6
        minute = bytes[1] % 6 * 10
        return Event(temperature=temperature, hour=hour, minute=minute)

    def toBytes(self) -> bytearray:

        return bytearray([self.temperature.toByte(), self.hour * 6 + self.minute // 10])

    def to_dict(self) -> dict:

        return {
            "temperature": self.temperature.to_dict(),
            "until": f"{self.hour:02}:{self.minute:02}"
        }

    def __str__(self):

        return f"Event(temperature={str(self.temperature)}, until={self.hour:02}:{self.minute:02})"
