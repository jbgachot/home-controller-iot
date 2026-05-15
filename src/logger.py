import time

import config


class Logger:
    LEVELS = ["debug", "info", "warning", "error"]

    def __init__(self, level):
        self.level = level

    def _should_log(self, level):
        return self.LEVELS.index(self.level) <= self.LEVELS.index(level)

    def _log(self, level, msg: str, args, prefix: str = ""):
        if not self._should_log(level):
            return
        _level = level.upper()
        _msg = msg % tuple(args) if args else msg
        _time = time.ticks_ms()
        _prefix = f"{prefix} | " if prefix else ""
        print(f"[{_time: >10}] {_level: >7} | {_prefix}{_msg}")

    def debug(self, msg, *args):
        self._log("debug", msg, args)

    def log(self, msg, *args):
        self._log("info", msg, args)

    def info(self, msg, *args):
        self._log("info", msg, args)

    def warning(self, msg, *args):
        self._log("warning", msg, args)

    def error(self, msg, *args):
        self._log("error", msg, args)

    def prefix(self, prefix: str):
        return PrefixLogger(self, prefix)


class PrefixLogger(Logger):
    def __init__(self, logger: Logger, prefix: str):
        super().__init__(logger.level)
        self.logger = logger
        self.prefix = prefix

    def _log(self, level, msg, args, prefix=""):
        self.logger._log(level, msg, args, prefix=prefix or self.prefix)


logger = Logger(getattr(config, "LOG_LEVEL", "info"))
