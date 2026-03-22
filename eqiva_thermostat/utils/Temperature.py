from typing import Optional

from .EqivaException import EqivaException


class Temperature:

    def __init__(self, valueC: Optional[float] = None):

        if valueC is not None and (valueC < -4.5 or valueC > 30.0 or valueC * 10 % 5 != 0):
            raise EqivaException(
                message='valueC must be between -4.5 and 30.0 in steps of 0.5. Offset temperature can be between -4.5 and 4.5. All other temperatures must be between 4.5 and 30.0')

        self.valueC: Optional[float] = valueC

    @staticmethod
    def fromByte(raw: int) -> 'Temperature':

        t = Temperature()
        t.valueC = raw / 2
        return t

    def _get_valueC(self) -> float:

        if self.valueC is None:
            raise EqivaException(message='Temperature value is not set')
        return self.valueC

    def toByte(self) -> int:

        return int(self._get_valueC() * 2)

    def fahrenheit(self) -> float:

        return (self._get_valueC() * 9.0/5.0) + 32.0

    def to_dict(self) -> dict:

        return {
            "valueC": self.valueC,
            "valueF": self.fahrenheit()
        }

    def __str__(self):

        return f"Temperature(celcius={self.valueC:.1f}°C, fahrenheit={self.fahrenheit():.1f}°F)"
