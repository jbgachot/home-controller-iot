"""Home Assistant thermostat service — auto-discovers and manages climate entities"""

import config
from src.ha_client import HAClient
from src.logger import logger
from src.models import ROOMS, Room

_log = logger.prefix("ha_service")
_service = None


class HAService:
    def __init__(self, client: HAClient):
        self._client = client

    def connect(self):
        """Connect and authenticate with Home Assistant"""
        return self._client.connect()

    @property
    def connected(self):
        return self._client.connected and self._client.authenticated

    def discover_thermostats(self):
        """Auto-discover all climate entities and populate the ROOMS registry.

        Also adds an optional outdoor sensor as a read-only tile if
        config.HA_OUTDOOR_ENTITY is set.

        Returns the number of thermostats discovered.
        """
        states = self._client.get_all_states()
        if states is None:
            _log.error("Failed to fetch states from Home Assistant")
            return 0

        ROOMS.clear()

        outdoor_entity = getattr(config, "HA_OUTDOOR_ENTITY", None)
        if outdoor_entity:
            for state in states:
                if state.get("entity_id") == outdoor_entity:
                    name = _entity_name(outdoor_entity)
                    attrs = state.get("attributes", {})
                    temp = _parse_temp(state.get("state")) or _parse_temp(
                        attrs.get("temperature")
                    )
                    ROOMS[name] = Room(
                        name, entity_id=outdoor_entity, actual_temp=temp, desired_temp=None
                    )
                    _log.debug("Added outdoor sensor: %s (%.1f°)", name, temp or 0)
                    break

        for state in states:
            entity_id = state.get("entity_id", "")
            if not entity_id.startswith("climate."):
                continue
            name = _entity_name(entity_id)
            attrs = state.get("attributes", {})
            actual = _parse_temp(attrs.get("current_temperature"))
            desired = _parse_temp(attrs.get("temperature"))
            hvac_action = attrs.get("hvac_action")
            hvac_mode = state.get("state")
            ROOMS[name] = Room(name, entity_id=entity_id, actual_temp=actual, desired_temp=desired, hvac_action=hvac_action, hvac_mode=hvac_mode)
            _log.debug(
                "Discovered thermostat: %s (current=%.1f° target=%.1f°)",
                name,
                actual or 0,
                desired or 0,
            )

        count = sum(1 for r in ROOMS.values() if r.entity_id and r.entity_id.startswith("climate."))
        _log.info("Discovered %s thermostat(s)", count)
        return count

    def sync_states(self):
        """Refresh all room temperatures from Home Assistant current state.

        Returns True if sync succeeded.
        """
        if not self.connected:
            _log.warning("Not connected, skipping sync")
            return False

        states = self._client.get_all_states()
        if states is None:
            return False

        entity_map = {s["entity_id"]: s for s in states if "entity_id" in s}
        for room in ROOMS.values():
            if not room.entity_id:
                continue
            state = entity_map.get(room.entity_id)
            if not state:
                continue
            attrs = state.get("attributes", {})
            if room.entity_id.startswith("climate."):
                room.actual_temp = _parse_temp(attrs.get("current_temperature"))
                room.desired_temp = _parse_temp(attrs.get("temperature"))
                room.hvac_action = attrs.get("hvac_action")
                room.hvac_mode = state.get("state")
            else:
                room.actual_temp = _parse_temp(state.get("state")) or _parse_temp(
                    attrs.get("temperature")
                )

        _log.debug("States synced for %s room(s)", len(ROOMS))
        return True

    def set_temperature(self, room_name, temp):
        """Set the target temperature for a thermostat in Home Assistant.

        Returns True on success.
        """
        room = ROOMS.get(room_name)
        if not room or not room.entity_id or not room.entity_id.startswith("climate."):
            _log.warning("Cannot set temperature: %s is not a climate entity", room_name)
            return False
        success = self._client.call_service(
            "climate",
            "set_temperature",
            service_data={"temperature": temp},
            target={"entity_id": room.entity_id},
        )
        if success:
            _log.info("Set %s to %.1f°", room_name, temp)
        else:
            _log.error("Failed to set temperature for %s", room_name)
        return success


    def set_hvac_mode(self, room_name, mode):
        """Set the HVAC mode (heat / off) for a thermostat in Home Assistant."""
        room = ROOMS.get(room_name)
        if not room or not room.entity_id or not room.entity_id.startswith("climate."):
            _log.warning("Cannot set mode: %s is not a climate entity", room_name)
            return False
        success = self._client.call_service(
            "climate",
            "set_hvac_mode",
            service_data={"hvac_mode": mode},
            target={"entity_id": room.entity_id},
        )
        if success:
            _log.info("Set %s mode to %s", room_name, mode)
        else:
            _log.error("Failed to set mode for %s", room_name)
        return success


def _entity_name(entity_id):
    """'climate.salon' → 'salon'"""
    return entity_id.split(".", 1)[-1]


def _parse_temp(value):
    """Safely parse any temperature value to float, returns None on failure"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def init(url, token):
    """Create and store the global HAService instance"""
    global _service
    _service = HAService(HAClient(url, token))
    return _service


def get():
    """Return the global HAService instance (None if not yet initialized)"""
    return _service
