class Mode():

    AUTO = 0x00
    MANUAL = 0x01
    VACATION = 0x02
    BOOST = 0x04
    DAYLIGHT_SUMMER_TIME = 0x08
    OPEN_WINDOW = 0x10
    LOCKED = 0x20
    UNKNOWN = 0x40
    BATTERY_LOW = 0x80

    MODES = ["AUTO", "MANUAL", "VACATION", "BOOST", "DAYLIGHT_SUMMER_TIME",
             "OPEN_WINDOW", "LOCKED", "UNKNOWN", "BATTERY_LOW"]

    def __init__(self, mode: int):

        self.mode = mode

    def to_dict(self) -> dict:

        modes = [Mode.MODES[0]
                 ] if self.mode & Mode.MANUAL != Mode.MANUAL else list()
        modes.extend([m for i, m in enumerate(
            Mode.MODES[1:]) if self.mode & 2**i == 2**i])
        return modes

    def __str__(self):

        return "Mode(modes=[%s])" % (",".join(self.to_dict()))
