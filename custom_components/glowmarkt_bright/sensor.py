"""Sensor platform for Glowmarkt Bright."""
import logging
from datetime import datetime, timedelta
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DOMAIN = "glowmarkt_bright"
SCAN_INTERVAL = timedelta(minutes=30)

# API Configuration
API_BASE_URL = "https://api.glowmarkt.com/api/v0-1"
AUTH_URL = f"{API_BASE_URL}/auth"
VIRTUAL_ENTITY_URL = f"{API_BASE_URL}/virtualentity"
RESOURCE_URL = f"{API_BASE_URL}/resource"

# Configuration keys
CONF_APPLICATION_ID = "application_id"


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Glowmarkt Bright sensor platform."""
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    application_id = config.get(CONF_APPLICATION_ID, "b0f1b774-a586-4f72-9edd-27ead8aa7a8d")

    if not username or not password:
        _LOGGER.error("Missing username or password in configuration")
        return

    # Create API client
    api_client = GlowmarktBrightAPI(username, password, application_id)

    # Test authentication
    try:
        await hass.async_add_executor_job(api_client.authenticate)
    except Exception as e:
        _LOGGER.error("Failed to authenticate with Glowmarkt API: %s", e)
        return

    # Get virtual entities (meters)
    try:
        entities = await hass.async_add_executor_job(api_client.get_virtual_entities)
    except Exception as e:
        _LOGGER.error("Failed to get virtual entities: %s", e)
        return

    if not entities:
        _LOGGER.warning("No virtual entities found")
        return

    _LOGGER.info("Found %d virtual entities to process", len(entities))

    # Create sensors
    sensors = []
    for entity in entities:
        if not isinstance(entity, dict):
            _LOGGER.warning("Skipping invalid entity (not a dict): %s", type(entity).__name__)
            continue

        entity_id = entity.get("veId")
        entity_name = entity.get("name", "Unknown")

        if not entity_id:
            _LOGGER.warning("Entity missing veId, skipping: %s", entity.keys())
            continue

        _LOGGER.debug("Processing entity: %s (ID: %s)", entity_name, entity_id)

        # Get resources for this entity
        try:
            resources = await hass.async_add_executor_job(
                api_client.get_resources, entity_id
            )

            # Validate that resources is actually a list
            if not isinstance(resources, list):
                _LOGGER.error(
                    "Invalid resources response for entity %s: expected list, got %s. Response: %s",
                    entity_id,
                    type(resources).__name__,
                    resources
                )
                continue

            _LOGGER.debug("Processing %d resources for entity %s", len(resources), entity_id)

            for resource in resources:
                # Ensure resource is a dict
                if not isinstance(resource, dict):
                    _LOGGER.warning(
                        "Skipping invalid resource (not a dict): %s", resource
                    )
                    continue

                resource_id = resource.get("resourceId")
                resource_type = resource.get("resourceTypeId", "")
                classifier = resource.get("classifier", "")
                resource_name = resource.get("name", "")
                base_unit = resource.get("baseUnit", "")

                if not resource_id:
                    _LOGGER.warning("Resource missing resourceId, skipping: %s", resource)
                    continue

                classifier_lower = classifier.lower()
                resource_type_lower = resource_type.lower()
                resource_name_lower = resource_name.lower()
                base_unit_lower = base_unit.lower()

                # Determine sensor type based on classifier and unit
                sensor_type = None
                sensor_name = None

                # Electricity consumption (kWh)
                if ("electricity" in classifier_lower and "consumption" in classifier_lower and
                    "cost" not in classifier_lower) or \
                   (base_unit_lower in ["kwh", "wh"] and "electricity" in resource_type_lower and
                    "cost" not in classifier_lower):
                    sensor_type = "electricity_consumption"
                    sensor_name = f"{entity_name} Electricity"

                # Electricity cost (pence/GBP)
                elif "electricity" in classifier_lower and "cost" in classifier_lower:
                    sensor_type = "electricity_cost"
                    sensor_name = f"{entity_name} Electricity Cost"

                # Gas consumption (kWh)
                elif ("gas" in classifier_lower and "consumption" in classifier_lower and
                      "cost" not in classifier_lower) or \
                     (base_unit_lower in ["kwh", "wh"] and "gas" in resource_type_lower and
                      "cost" not in classifier_lower):
                    sensor_type = "gas_consumption"
                    sensor_name = f"{entity_name} Gas"

                # Gas cost (pence/GBP)
                elif "gas" in classifier_lower and "cost" in classifier_lower:
                    sensor_type = "gas_cost"
                    sensor_name = f"{entity_name} Gas Cost"

                # Standing charge
                elif "standing" in classifier_lower or "standing" in resource_name_lower:
                    sensor_type = "standing_charge"
                    sensor_name = f"{entity_name} Standing Charge"

                # Tariff/rate
                elif "tariff" in classifier_lower or "rate" in classifier_lower or \
                     "tariff" in resource_name_lower or "rate" in resource_name_lower:
                    sensor_type = "tariff"
                    sensor_name = f"{entity_name} Tariff Rate"

                else:
                    _LOGGER.debug(
                        "Skipping unrecognized resource '%s' (classifier: %s, unit: %s)",
                        resource_name,
                        classifier,
                        base_unit
                    )
                    continue

                # Create the sensor
                if sensor_type and sensor_name:
                    sensors.append(
                        GlowmarktBrightSensor(
                            api_client,
                            entity_id,
                            resource_id,
                            sensor_name,
                            sensor_type,
                            base_unit,
                        )
                    )
                    _LOGGER.info(
                        "Created %s sensor: %s (resource: %s, classifier: %s, unit: %s)",
                        sensor_type,
                        sensor_name,
                        resource_name,
                        classifier,
                        base_unit
                    )
                    _LOGGER.info(
                        "Created gas sensor for %s (resource: %s, classifier: %s, unit: %s)",
                        entity_name,
                        resource_name,
                        classifier,
                        base_unit
                    )
                else:
                    _LOGGER.debug(
                        "Skipping resource '%s' (ID: %s, classifier: %s) - not a consumption resource",
                        resource_name,
                        resource_id,
                        classifier
                    )
        except Exception as e:
            _LOGGER.error("Failed to get resources for entity %s: %s", entity_id, e, exc_info=True)

    if sensors:
        async_add_entities(sensors, True)
        _LOGGER.info("Added %d Glowmarkt Bright sensors", len(sensors))
    else:
        _LOGGER.warning("No sensors found for Glowmarkt Bright")


class GlowmarktBrightAPI:
    """API client for Glowmarkt Bright."""

    def __init__(self, username: str, password: str, application_id: str):
        """Initialize the API client."""
        self.username = username
        self.password = password
        self.application_id = application_id
        self.token = None
        self.token_expiry = None
        self.session = requests.Session()

    def authenticate(self) -> str:
        """Authenticate and get access token."""
        # Check if we have a valid token
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.token

        _LOGGER.debug("Authenticating with Glowmarkt API")

        headers = {
            "applicationId": self.application_id,
            "Content-Type": "application/json",
        }

        try:
            response = self.session.post(
                AUTH_URL,
                json={"username": self.username, "password": self.password},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            self.token = data.get("token")

            # Tokens typically last 24 hours, refresh after 23 hours to be safe
            self.token_expiry = datetime.now() + timedelta(hours=23)

            _LOGGER.info("Successfully authenticated with Glowmarkt API")
            return self.token

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Authentication failed: %s", e)
            raise

    def get_virtual_entities(self) -> list:
        """Get list of virtual entities (meters)."""
        token = self.authenticate()

        headers = {
            "applicationId": self.application_id,
            "token": token,
        }

        try:
            response = self.session.get(
                VIRTUAL_ENTITY_URL,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # Validate the response is a list
            if not isinstance(data, list):
                _LOGGER.error(
                    "Invalid response from get_virtual_entities: expected list, got %s. Response: %s",
                    type(data).__name__,
                    data
                )
                return []

            _LOGGER.debug("Got %d virtual entities", len(data))
            return data

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Failed to get virtual entities: %s", e)
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error getting virtual entities: %s", e, exc_info=True)
            return []

    def get_resources(self, entity_id: str) -> list:
        """Get resources for a virtual entity."""
        token = self.authenticate()

        headers = {
            "applicationId": self.application_id,
            "token": token,
        }

        url = f"{VIRTUAL_ENTITY_URL}/{entity_id}/resources"

        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # The API returns a dict with a 'resources' key containing the list
            if isinstance(data, dict):
                if "resources" in data:
                    resources = data["resources"]
                    if isinstance(resources, list):
                        _LOGGER.debug("Got %d resources for entity %s", len(resources), entity_id)
                        return resources
                    else:
                        _LOGGER.error(
                            "Invalid resources type for entity %s: expected list, got %s",
                            entity_id,
                            type(resources).__name__
                        )
                        return []
                else:
                    _LOGGER.error(
                        "No 'resources' key found in response for entity %s. Keys: %s",
                        entity_id,
                        list(data.keys())
                    )
                    return []
            elif isinstance(data, list):
                # Fallback: API might return a list directly in some cases
                _LOGGER.debug("Got %d resources (direct list) for entity %s", len(data), entity_id)
                return data
            else:
                _LOGGER.error(
                    "Invalid response from get_resources for entity %s: expected dict or list, got %s",
                    entity_id,
                    type(data).__name__
                )
                return []

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Failed to get resources for entity %s: %s", entity_id, e)
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error getting resources for entity %s: %s", entity_id, e, exc_info=True)
            return []

    def get_readings(
        self,
        resource_id: str,
        from_date: datetime,
        to_date: datetime,
        period: str = "PT30M",
        function: str = "sum",
    ) -> dict:
        """Get readings for a resource.

        Args:
            resource_id: The resource ID
            from_date: Start date/time
            to_date: End date/time
            period: Period format (PT30M = 30 minutes, P1D = 1 day)
            function: Aggregation function (sum, avg, max, min)
        """
        token = self.authenticate()

        headers = {
            "applicationId": self.application_id,
            "token": token,
        }

        # Format dates as ISO 8601
        from_str = from_date.strftime("%Y-%m-%dT%H:%M:%S")
        to_str = to_date.strftime("%Y-%m-%dT%H:%M:%S")

        url = f"{RESOURCE_URL}/{resource_id}/readings"
        params = {
            "from": from_str,
            "to": to_str,
            "period": period,
            "function": function,
        }

        try:
            response = self.session.get(
                url,
                headers=headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            return data

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Failed to get readings for resource %s: %s", resource_id, e)
            raise


class GlowmarktBrightSensor(SensorEntity):
    """Representation of a Glowmarkt Bright sensor."""

    def __init__(
        self,
        api_client: GlowmarktBrightAPI,
        entity_id: str,
        resource_id: str,
        name: str,
        resource_type: str,
        base_unit: str = "",
    ):
        """Initialize the sensor."""
        self._api_client = api_client
        self._entity_id = entity_id
        self._resource_id = resource_id
        self._name = name
        self._resource_type = resource_type
        self._base_unit = base_unit
        self._state = None
        self._attributes = {}
        self._available = True
        self._last_reading_time = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"glowmarkt_{self._resource_id}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        # Cost sensors use currency
        if "cost" in self._resource_type or "charge" in self._resource_type or "tariff" in self._resource_type:
            # Always use GBP for cost sensors
            # API returns pence, we'll convert to GBP (divide by 100)
            return "GBP"
        # Consumption sensors use energy
        else:
            return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return the device class."""
        # Consumption sensors are energy
        if "consumption" in self._resource_type:
            return SensorDeviceClass.ENERGY
        # Cost sensors are monetary value
        elif "cost" in self._resource_type or "charge" in self._resource_type:
            return SensorDeviceClass.MONETARY
        # Tariff/rate sensors have no specific device class
        else:
            return None

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return the state class."""
        # Consumption and cost sensors should be total_increasing for cumulative totals
        if "consumption" in self._resource_type or "cost" in self._resource_type or "charge" in self._resource_type:
            return SensorStateClass.TOTAL_INCREASING
        # Tariff rates are measurements (current rate)
        elif "tariff" in self._resource_type:
            return SensorStateClass.MEASUREMENT
        else:
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            "entity_id": self._entity_id,
            "resource_id": self._resource_id,
            "resource_type": self._resource_type,
        }
        if self._last_reading_time:
            attrs["last_reading_time"] = self._last_reading_time.isoformat()
        attrs.update(self._attributes)
        return attrs

    @Throttle(SCAN_INTERVAL)
    def update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            # Get readings from exactly 24 hours ago
            # For example, at 3pm on March 16th, fetch data from 3pm March 14th to 3pm March 15th
            to_date = datetime.now() - timedelta(hours=24)
            from_date = to_date - timedelta(hours=24)

            data = self._api_client.get_readings(
                self._resource_id,
                from_date,
                to_date,
                period="PT30M",  # 30-minute intervals
                function="sum",
            )

            # Calculate cumulative total from all readings
            if data and "data" in data:
                readings = data["data"]
                if readings:
                    _LOGGER.debug(
                        "Got %d readings for %s. First: %s, Last: %s",
                        len(readings),
                        self._name,
                        readings[0] if readings else None,
                        readings[-1] if readings else None,
                    )

                    # Calculate cumulative total and find latest valid timestamp
                    cumulative_total = 0
                    latest_timestamp = None
                    valid_reading_count = 0

                    # Process all readings to build cumulative total
                    for reading in readings:
                        if len(reading) >= 2:
                            timestamp = reading[0]
                            value = reading[1]

                            # Convert timestamp to datetime
                            if timestamp > 0:
                                try:
                                    reading_time = datetime.fromtimestamp(timestamp)

                                    # Skip readings from 1970 (invalid timestamps)
                                    if reading_time.year >= 2020 and value is not None:
                                        cumulative_total += float(value)
                                        latest_timestamp = reading_time
                                        valid_reading_count += 1
                                except (ValueError, OSError) as e:
                                    _LOGGER.warning(
                                        "Invalid timestamp %s for %s: %s",
                                        timestamp,
                                        self._name,
                                        e
                                    )
                                    continue

                    if valid_reading_count > 0:
                        # For cost sensors, convert pence to GBP
                        if "cost" in self._resource_type or "charge" in self._resource_type:
                            self._state = round(cumulative_total / 100, 2)  # Convert pence to GBP
                        else:
                            self._state = round(cumulative_total, 3)  # kWh sensors keep 3 decimals

                        self._last_reading_time = latest_timestamp

                        # Store additional attributes
                        self._attributes = {
                            "total_readings": len(readings),
                            "valid_readings": valid_reading_count,
                            "data_range_from": from_date.isoformat(),
                            "data_range_to": to_date.isoformat(),
                            "last_reading_time": latest_timestamp.isoformat() if latest_timestamp else None,
                        }

                        self._available = True
                        _LOGGER.info(
                            "Updated %s: %s %s (cumulative from %d readings, last: %s)",
                            self._name,
                            self._state,
                            self.native_unit_of_measurement,
                            valid_reading_count,
                            latest_timestamp.isoformat() if latest_timestamp else "unknown",
                        )
                    else:
                        _LOGGER.warning("No valid readings found for %s in %d readings", self._name, len(readings))
                        self._available = False
                else:
                    _LOGGER.warning("No readings available for %s", self._name)
                    self._available = False
            else:
                _LOGGER.warning("No data returned for %s", self._name)
                self._available = False

        except Exception as e:
            _LOGGER.error("Error updating %s: %s", self._name, e, exc_info=True)
            self._available = False
