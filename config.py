# core
NTP_SERVER = None
DISABLE_WIFI = False
BUZZER_VOLUME = 100

# home assistant
HA_OUTDOOR_ENTITY = None  # Optional entity_id for outdoor sensor, e.g. "weather.home"
HA_WEATHER_ENTITY = "weather.paris"  # Optional weather entity for forecast section
HA_SYNC_INTERVAL_MS = 15000  # Sync thermostat states every 30 seconds

# debugging
DEBUG = False
LOG_LEVEL = "debug" if DEBUG else "info"
