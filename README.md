# tapVerkada

A small Python script that polls the [Verkada](https://www.verkada.com/) Cameras API for the most recent
"person of interest" and, when that person is `Nate`, triggers Philips Hue lights through the local Hue bridge.

## How it works

1. `auth()` exchanges your Verkada API key for a short-lived auth token.
2. `poll_camera()` requests the latest person of interest and prints who it was and when they were last seen (Pacific time).
3. If the person is POI_USER, `get_lights()` lists the lights on the Hue bridge and `turn_on_lights()` sends each one a state change.
4. `main()` repeats the poll every second, refreshing the token every ~30 minutes.

## Requirements

- Python 3.9+ (uses `zoneinfo`)
- A Verkada API key
- A Philips Hue bridge reachable on your local network, plus a registered Hue username (application key)

Install dependencies:

```bash
pip install requests urllib3 python-dotenv
```

On Windows, `zoneinfo` may also need `pip install tzdata`.

## Configuration

Create a `.env` file in the project root (it is git-ignored, so keep secrets out of version control):

```
VERKADA_API_KEY=your-verkada-api-key
HUE_IP=192.168.1.x
HUE_USERNAME=your-hue-username
POI_USER=POI user in Verkada Command
```

## Usage

```bash
python poll_camera.py
```

## Known issues

The script is a work in progress and has bugs that prevent it from running end to end:

- `get_lights()` compares `reachable` to the string `"true"` (the Hue API returns a boolean) and returns `light_name` (last name) instead of `light_names`; the caller then unpacks it as `(light, name)` pairs.
- `turn_on_lights()` sends `{"off": true}` (Hue expects `{"on": true}`) and indexes the `requests` response object directly instead of `response.json()`.
