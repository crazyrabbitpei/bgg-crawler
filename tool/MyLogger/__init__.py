import logging
from logging import Logger
from logging.handlers import TimedRotatingFileHandler
import sys

logging.basicConfig(level=logging.DEBUG)

class MyLogger(Logger):
    def __init__(self, log_file=None, log_format='%(asctime)s - %(levelname)s - %(message)s', *args, **kwargs):
        self.formatter = logging.Formatter(log_format)
        self.log_file = log_file

        Logger.__init__(self, *args, **kwargs)
        self.addHandler(self.set_console_handler())
        if log_file:
            self.addHandler(self.set_file_handler())


        self.propagate = False

    def set_console_handler(self):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.formatter)
        handler.setLevel(logging.ERROR)
        return handler

    def set_file_handler(self):
        handler = TimedRotatingFileHandler(
            self.log_file, when='D', interval=1, backupCount=3)
        handler.setFormatter(self.formatter)
        handler.setLevel(logging.DEBUG)
        return handler
