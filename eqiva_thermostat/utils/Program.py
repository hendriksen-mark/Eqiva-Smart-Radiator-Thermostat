from .Event import Event
from .EqivaException import EqivaException

class Program():

    DAY_SATURDAY = 0x00
    DAY_SUNDAY = 0x01
    DAY_MONDAY = 0x02
    DAY_TUESDAY = 0x03
    DAY_WEDNESDAY = 0x04
    DAY_THURSDAY = 0x05
    DAY_FRIDAY = 0x06
    DAY_WEEKEND = 0x07
    DAY_WORKDAY = 0x08
    DAY_EVERYDAY = 0x09
    DAY_TODAY = 0x0A
    DAY_TOMORROW = 0x0B

    DAYS = ["sat", "sun", "mon", "tue", "wed", "thu", "fri",
            "weekend", "work", "everyday", "today", "tomorrow"]

    DAYS_LONG = ["Saturday", "Sunday", "Monday",
                 "Tuesday", "Wednesday", "Thursday", "Friday"]

    def __init__(self, events: list = list()):

        if not events:
            raise EqivaException('No events given')
        elif len(events) > 7:
            raise EqivaException(
                'More than 7 events given but maximum is 7 events per day')

        self.events: list = events

    @staticmethod
    def fromBytes(bytes: bytearray) -> 'Program':

        events = list()
        for i in range(7):
            events.append(Event.fromBytes(bytes[i * 2: i * 2 + 2]))

        return Program(events=events)

    def toBytes(self) -> bytearray:

        bytes = list()
        for e in self.events:
            bytes.extend(e.toBytes())

        if len(bytes) < 14:
            bytes.extend([0] * (14 - len(bytes)))

        return bytearray(bytes)

    def to_dict(self) -> dict:

        return [e.to_dict() for e in self.events if e.hour != 0]

    def __str__(self):

        return "Program(%s)" % (", ".join([str(e) for e in self.events if e.hour != 0]))
