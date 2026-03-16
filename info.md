# Hildebrand Glow (DCC) / Glowmarkt Bright

Integrate your Hildebrand Glow smart meter data into Home Assistant!

## Features

✅ Electricity consumption and cost tracking  
✅ Gas consumption and cost tracking  
✅ Standing charges and tariff rates  
✅ Energy Dashboard compatible  
✅ Automatic updates every 30 minutes  

## Quick Start

After installation, add to your `configuration.yaml`:

```yaml
sensor:
  - platform: glowmarkt_bright
    username: YOUR_EMAIL
    password: YOUR_PASSWORD
```

Then restart Home Assistant. Your sensors will be automatically discovered!

## Need Help?

See the [full documentation](https://github.com/josephsmith0705/ha-hildebrandglow-dcc) for detailed setup instructions and troubleshooting.
