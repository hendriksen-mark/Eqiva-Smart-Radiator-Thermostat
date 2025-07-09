from datetime import datetime, timedelta

class Vacation():

    def __init__(self, until: datetime = None):

        self.until: datetime = (
            until - timedelta(minutes=until.minute % 30)) if until else None

    @staticmethod
    def fromBytes(bytes: bytearray) -> 'Vacation':

        v = Vacation()
        if bytes[0] > 0:
            v.until = datetime(day=bytes[0], month=bytes[3], year=2000 +
                               bytes[1], hour=bytes[2] // 2, minute=bytes[2] % 2 * 30)
        return v

    def toBytes(self) -> bytearray:

        return bytearray([self.until.day, self.until.year - 2000, self.until.hour * 2 + self.until.minute // 30, self.until.month])

    def to_dict(self) -> dict:

        return {
            "until": (self.until.strftime("%Y-%m-%d %H:%M") if self.until else None)
        }

    def __str__(self):

        return "Vacation(until=%s)" % (self.until.strftime("%Y-%m-%d %H:%M") if self.until else "off")
