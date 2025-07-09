from utils.Temperature import Temperature
from utils.EqivaException import EqivaException

class OpenWindowConfig():

    def __init__(self, temperature: Temperature = None, minutes: int = 0):

        if minutes < 0 or minutes > 995 or minutes % 5 != 0:
            raise EqivaException(
                message='minutes must be between 5 and 995 in steps of 5')

        self.minutes: int = minutes
        self.temperature: Temperature = temperature

    @staticmethod
    def fromBytes(bytes: bytearray) -> 'OpenWindowConfig':

        w = OpenWindowConfig()
        w.temperature = Temperature.fromByte(bytes[0])
        w.minutes = bytes[1] * 5
        return w

    def toBytes(self) -> bytearray:

        return bytearray([self.temperature.toByte(), self.minutes // 5])

    def to_dict(self) -> dict:

        return {
            "temperature": self.temperature.to_dict(),
            "minutes": self.minutes
        }

    def __str__(self):

        return f"OpenWindowConfig(minutes={self.minutes}, temperature={str(self.temperature)})"
