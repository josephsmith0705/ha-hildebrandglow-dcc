# Hildebrand Glow (DCC) / Glowmarkt Bright Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

This custom integration allows you to integrate your Hildebrand Glow (DCC) smart meter data into Home Assistant via the Glowmarkt Bright API. It provides real-time access to your electricity and gas consumption and cost data.

## Features

- **Electricity Consumption**: Monitor your electricity usage in kWh
- **Electricity Cost**: Track electricity costs in GBP
- **Gas Consumption**: Monitor your gas usage in kWh
- **Gas Cost**: Track gas costs in GBP
- **Standing Charges**: View standing charges
- **Tariff Rates**: See current tariff rates
- **Automatic Updates**: Data refreshes every 30 minutes
- **Energy Dashboard Compatible**: Works seamlessly with Home Assistant's Energy Dashboard

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Add"
7. Find "Hildebrand Glow (DCC) / Glowmarkt Bright" in the list and click "Download"
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from this repository
2. Copy the `custom_components/glowmarkt_bright` folder to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

This integration is configured via `configuration.yaml`:

```yaml
sensor:
  - platform: glowmarkt_bright
    username: YOUR_EMAIL
    password: YOUR_PASSWORD
    application_id: b0f1b774-a586-4f72-9edd-27ead8aa7a8d  # Optional, uses default if not specified
```

### Configuration Variables

- **username** (*Required*): Your Glowmarkt/Hildebrand Glow account email
- **password** (*Required*): Your Glowmarkt/Hildebrand Glow account password
- **application_id** (*Optional*): Application ID for the API (default is provided)

### Getting Your Credentials

1. If you have a Hildebrand Glow IHD (In-Home Display), you already have a Glowmarkt account
2. Visit [Bright App](https://glowmarkt.com/consumers/bright) to access your account
3. Use the same email and password you use to log into the Bright app

## Sensors Created

The integration will automatically discover and create sensors for all available meters and resources:

- `sensor.<meter_name>_electricity` - Electricity consumption (kWh)
- `sensor.<meter_name>_electricity_cost` - Electricity cost (GBP)
- `sensor.<meter_name>_gas` - Gas consumption (kWh)
- `sensor.<meter_name>_gas_cost` - Gas cost (GBP)
- `sensor.<meter_name>_standing_charge` - Standing charge (GBP)
- `sensor.<meter_name>_tariff_rate` - Current tariff rate (GBP/kWh)

## Using with Energy Dashboard

The consumption sensors (electricity and gas) are compatible with Home Assistant's Energy Dashboard:

1. Go to Settings → Dashboards → Energy
2. Click "Add Consumption" under Electricity grid or Gas consumption
3. Select your `sensor.<meter_name>_electricity` or `sensor.<meter_name>_gas` sensor
4. The cost sensors will automatically appear as optional cost tracking

## Troubleshooting

### No sensors appearing

1. Check your credentials are correct
2. Enable debug logging to see detailed information:

```yaml
logger:
  default: info
  logs:
    custom_components.glowmarkt_bright: debug
```

3. Restart Home Assistant and check the logs

### Data not updating

- The Glowmarkt API may have delays (typically up to 12 hours for some data)
- The integration polls every 30 minutes
- Check the `last_reading_time` attribute on your sensors to see when data was last received

### Authentication errors

- Verify your username and password are correct
- Try logging into the [Bright App](https://glowmarkt.com/consumers/bright) to confirm your credentials work
- Check that your account is active and has access to meter data

## API Information

This integration uses the Glowmarkt Bright API v0.1:
- Base URL: `https://api.glowmarkt.com/api/v0-1`
- Authentication tokens are automatically managed and refreshed
- Data is retrieved in 30-minute intervals over the last 24 hours

## Support

For issues, questions, or feature requests, please open an issue on [GitHub](https://github.com/josephsmith0705/ha-hildebrandglow-dcc/issues).

## Credits

Developed for the Home Assistant community to integrate Hildebrand Glow DCC smart meter data.

## License

MIT License - See LICENSE file for details
