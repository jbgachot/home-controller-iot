"""Data models for thermostat rooms"""

_DAYS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


class ForecastDay:
    def __init__(self, datetime_str, condition, temp_max, temp_min, precipitation_probability=0):
        self._datetime_str = datetime_str
        self.condition = condition
        self.temp_max = temp_max
        self.temp_min = temp_min
        self.precipitation_probability = precipitation_probability

    @property
    def day_abbr(self):
        try:
            date = self._datetime_str[:10]
            year, month, day = int(date[:4]), int(date[5:7]), int(date[8:10])
            if month < 3:
                month += 12
                year -= 1
            k = year % 100
            j = year // 100
            h = (day + (13 * (month + 1)) // 5 + k + k // 4 + j // 4 - 2 * j) % 7
            return _DAYS_FR[(h + 5) % 7]
        except Exception:
            return "?"


class WeatherData:
    def __init__(self):
        self.condition = None
        self.temperature = None
        self.temp_high = None
        self.temp_low = None
        self.forecast = []  # list of ForecastDay for next 5 days


WEATHER = WeatherData()


class Room:
    def __init__(self, name, entity_id=None, actual_temp=None, desired_temp=None, hvac_action=None, hvac_mode=None):
        self.name = name
        self.entity_id = entity_id
        self.actual_temp = actual_temp
        self.desired_temp = desired_temp
        self.hvac_action = hvac_action  # "heating", "idle", "off", or None
        self.hvac_mode = hvac_mode      # "heat", "off", or None

    @property
    def actual_temp_str(self):
        if self.actual_temp is None:
            return "-"
        return f"{int(self.actual_temp)}°"

    @property
    def desired_temp_str(self):
        if self.desired_temp is None:
            return "-"
        return f"{self.desired_temp:.1f}°"

    def set_desired_temp(self, temp):
        self.desired_temp = float(temp)

    def adjust_desired_temp(self, adjustment):
        if self.desired_temp is not None:
            self.desired_temp = round(self.desired_temp + adjustment, 1)

    def to_dict(self):
        return {
            "name": self.name,
            "entity_id": self.entity_id,
            "actual_temp": self.actual_temp,
            "desired_temp": self.desired_temp,
        }


# Global room registry — populated at runtime by ha_service.discover_thermostats()
ROOMS = {}


def get_room(name):
    return ROOMS.get(name)
