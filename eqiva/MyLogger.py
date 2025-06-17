import sys

class MyLogger():
    LEVELS = {
        "DEBUG": 0,
        "INFO": 1,
        "WARN": 2,
        "ERROR": 3
    }

    NAMES = ["DEBUG", "INFO", "WARN", "ERROR"]

    level = LEVELS["INFO"]  # Class variable for global log level

    def __init__(self, level: int = None) -> None:
        if level is not None:
            MyLogger.level = level  # Set global log level if provided

    def error(self, s: str):
        self.log(MyLogger.LEVELS["ERROR"], s)

    def warning(self, s: str):
        self.log(MyLogger.LEVELS["WARN"], s)

    def info(self, s: str):
        self.log(MyLogger.LEVELS["INFO"], s)

    def debug(self, s: str):
        self.log(MyLogger.LEVELS["DEBUG"], s)

    def log(self, level: int, s: str):
        if level >= MyLogger.level:
            print(f"{MyLogger.NAMES[level]}\t{s}", file=sys.stderr, flush=True)

    @staticmethod
    def hexstr(ba: bytearray) -> str:
        return " ".join([("0" + hex(b).replace("0x", ""))[-2:] for b in ba])
