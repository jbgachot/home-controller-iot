import asyncio
import config
import ntptime

from picovector import ANTIALIAS_BEST, PicoVector
from machine import PWM
from machine import Pin

from presto import Presto
from src.logger import logger

presto = Presto(full_res=False, ambient_light=False, layers=1)
touch = presto.touch
display = presto.display
rgb = display.create_pen
vector = PicoVector(display)
vector.set_antialiasing(ANTIALIAS_BEST)

async def setup_wifi():
    if getattr(config, "DISABLE_WIFI", False):
        return
    
    if host := getattr(config, "NTP_SERVER", None):
            ntptime.host = host
    
    while True:
        if presto.wifi.isconnected():
            await asyncio.sleep(15)
            continue

        try:
            await presto.async_connect()
            if presto.wifi.isconnected():
                logger.info("Networking connection established. IPv4: %s", presto.wifi.ipv4())
                ntptime.settime()
        except Exception as exc:
            logger.error(f"Unable to connect to WiFi. Error: {exc}.")


class Buzzer:
    NOTE_HOLD_TIME = 0.1
    NOTES = {
        "c": 262,
        "d": 294,
        "e": 330,
        "f": 349,
        "g": 392,
        "a": 440,
        "h": 494,
        "C": 523,
    }

    def __init__(self, pin, volume=100):
        self._pwm = PWM(pin)
        self.volume = volume

    @property
    def _volume(self):
        return round(self.volume * 10)

    async def buzz(self, freq=1000, time=NOTE_HOLD_TIME):
        if self.volume == 0:
            return
        try:
            if freq == 0:
                self._pwm.duty_u16(0)
            else:
                self._pwm.freq(freq)
                self._pwm.duty_u16(self._volume)
            await asyncio.sleep(time)
        finally:
            self._pwm.duty_u16(0)

    def _parse_melody(self, melody, notes):
        result = []
        last_freq = 0
        last_note = None
        count = 0
        for index, note in enumerate(melody + "."):
            if index != 0:
                count += 1
            if note != last_note:
                if count:
                    result.append([last_freq, count])
                count = 0
                last_note = note
                last_freq = notes.get(note, 0)
        return result

    async def play_melody(
        self,
        melody: str,
        *,
        bump: int = 1,
        notes: dict[str, int] = None,
        hold_time: float = None,
    ):
        notes = notes or self.NOTES
        hold_time = hold_time or self.NOTE_HOLD_TIME
        _melody = self._parse_melody(melody, notes)
        for [base_freq, hold_count] in _melody:
            freq = base_freq * bump
            hold_time = hold_count * hold_time
            await self.buzz(freq, hold_time)

    def create_melody(self, melody: str, **kwargs_wrapper):
        def _play_melody(**kwargs):
            _kwargs = dict(kwargs_wrapper)
            _kwargs.update(kwargs)
            return self.play_melody(melody, **_kwargs)

        return _play_melody
    
buzzer = Buzzer(Pin(43), getattr(config, "BUZZER_VOLUME", 100))
play_melody = buzzer.create_melody("g", bump=3)
# play_melody_meh = buzzer.create_melody("f.cc", bump=2)
# play_melody_ok = buzzer.create_melody("c.ff", bump=3)
# play_melody_start = buzzer.create_melody("CCC", bump=3)
# play_melody_stop = buzzer.create_melody("ccc", bump=1)