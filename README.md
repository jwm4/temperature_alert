# Temperature Alert System

A Python service that monitors temperatures from Ecowitt sensors and sends alerts via [ntfy.sh](https://ntfy.sh) if thresholds are exceeded or based on weather forecasts.

## Features

- **Ecowitt Integration**: Automatically discovers and reads data from Ecowitt GW1XXX gateways.
- **Freeze & Heat Warnings**: Alerts when indoor/outdoor temperatures cross defined thresholds.
- **Weather Forecast**: Integrates with Open-Meteo to check for upcoming temperature extremes.
- **Configurable**: Customize sensors, thresholds, and alert topics.

## Installation

1. Clone the repository.
2. Install dependencies (standard library only, no pip install needed unless extending).
3. Copy `config.example.json` to `config.json`.

## Configuration

Edit `config.json` with your settings:

```json
{
    "latitude": 42.79,
    "longitude": -74.62,
    "freeze_threshold_f": 60.0,
    "heat_threshold_f": 70.0,
    "ntfy_topic": "your-topic-here",
    "sensors": {
        "Indoor": "Kitchen",
        "Channel 1": "Living Room"
    }
}
```

- **sensors**: An ordered dictionary mapping sensor keys (e.g., "Channel 1") to display names (e.g., "Living Room"). The order here determines the order in alerts.

## Usage

Run the service:

```bash
python temperature_alert.py
```

It will run in a loop, polling sensors every 5 minutes and performing scheduled checks.
