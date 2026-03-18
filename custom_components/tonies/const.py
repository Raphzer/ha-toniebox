"""Constants for the Tonies integration."""

DOMAIN = "tonies"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DATA_COORDINATOR = "coordinator"

# Polling interval for Classic boxes (no WebSocket)
POLLING_INTERVAL_SECONDS = 300  # 5 minutes

# Platforms
PLATFORMS = ["media_player", "sensor", "switch", "select", "number"]

# Entity unique id prefixes
UNIQUE_ID_MEDIA_PLAYER = "toniebox_mediaplayer"
UNIQUE_ID_SENSOR_BATTERY = "toniebox_battery"
UNIQUE_ID_SENSOR_TONIE = "toniebox_tonie"
UNIQUE_ID_SENSOR_ONLINE = "toniebox_online"
UNIQUE_ID_SWITCH_SLEEP = "toniebox_sleep"
UNIQUE_ID_SELECT_LED = "toniebox_led"
UNIQUE_ID_NUMBER_VOLUME = "toniebox_volume"
UNIQUE_ID_NUMBER_HP_VOL = "toniebox_headphone_volume"
UNIQUE_ID_NUMBER_LED_BRIGHTNESS = "toniebox_led_brightness"
UNIQUE_ID_NUMBER_BEDTIME_VOLUME = "toniebox_bedtime_volume"
UNIQUE_ID_NUMBER_BEDTIME_HP_VOL = "toniebox_bedtime_headphone_volume"
UNIQUE_ID_NUMBER_BEDTIME_LED = "toniebox_bedtime_led_brightness"

# Attribute names
ATTR_TONIE_NAME = "tonie_name"
ATTR_TONIE_IMAGE = "tonie_image"
ATTR_TONIE_ID = "tonie_id"
ATTR_HOUSEHOLD_ID = "household_id"
ATTR_MAC_ADDRESS = "mac_address"
ATTR_HEADPHONES = "headphones_connected"

# Volume steps for Classic boxes
CLASSIC_VOLUME_STEPS = [25, 50, 75, 100]

# LED options
LED_OPTIONS = ["on", "dimmed", "off"]
