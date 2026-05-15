"""Data models for thermostat rooms"""


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
