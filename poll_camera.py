"""Poll Verkada for the most recent person of interest and react with Philips Hue lights.

Flow:
  1. Exchange the Verkada API key for a short-lived auth token (auth).
  2. Fetch the latest person of interest from the Verkada Cameras API (poll_camera).
  3. If that person is "Nate", look up the Hue lights on the local bridge (get_lights)
     and send each reachable light a state change (turn_on_lights).

Configuration is read from a .env file:
  VERKADA_API_KEY  - Verkada API key
  HUE_IP           - IP address of the Hue bridge on the local network
  HUE_USERNAME     - application key / username registered with the Hue bridge
  POI_USER         - name of POI in Verkada command
"""
import requests, urllib3
import os
import time
import logging
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Load VERKADA_API_KEY, HUE_IP and HUE_USERNAME from .env into the environment
load_dotenv()

# Silence urllib3 warnings (e.g. unverified HTTPS request warnings)
urllib3.disable_warnings()

# Hue bridge connection details
IP = os.getenv("HUE_IP")
USERNAME = os.getenv("HUE_USERNAME")
POI_USER = os.getenv("POI_USER")

def auth():
    """Request a Verkada API token using the API key and return it as a string."""
    url = "https://api.verkada.com/token"

    headers = {
        "accept": "application/json",
        "x-api-key": os.getenv("VERKADA_API_KEY")
        }

    response = requests.post(url, headers=headers)
    response_json = response.json()
    # The response body is JSON like {"token": "<value>"}; splitting on quotes
    # puts the token value at index 3
    token = response_json["token"]
    # Record when the token was issued 
    auth_timer = time.time()

    return [token, auth_timer]

def poll_camera(token):
    """Fetch the most recent person of interest and trigger the lights if it's POI_USER."""
    # page_size=1 returns only the single most recent person of interest
    url = "https://api.verkada.com/cameras/v1/people/person_of_interest?page_size=1"
    headers = {
        "accept": "application/json",
        "x-verkada-auth": token
        }

    response = requests.get(url, headers=headers)
    response = response.json()
    poi = response["persons_of_interest"][0]
    person = poi["label"]

    # last_seen is a Unix timestamp; display it in Pacific time
    last_seen = datetime.fromtimestamp(poi["last_seen"], tz=ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z")

    if person == POI_USER and (time.time() - poi["last_seen"]) > 1800:
        logger.info(f'{person} was last seen at {last_seen}, more than 30 minutes ago')
        # get_lights() returns [light_ids, light_name]; index 0 is the list of
        # reachable light IDs
        for item in get_lights()[0]:
            for num, light in enumerate(item):
                turn_on_lights(light, item[num])

def get_lights():
    """Query the Hue bridge for all lights and report which are reachable.

    Returns a list of [reachable light IDs, light name].
    """
    url = f'http://{IP}/api/{USERNAME}/lights'

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload).json()

    light_ids = []
    light_names = []

    # The Hue API returns a dict keyed by light ID
    for light_id, light in response.items():
        light_name = light["name"]
        if light["state"]["reachable"] == True and light["state"]["on"] == False:
            light_ids.append(light_id)
            light_names.append(light_name)
            logger.info(f'{light_name} is reachable and off.')
        elif light["state"]["reachable"]:
            logger.info(f'{light_name} is reachable')
        else:
            logger.warning(f'{light_name} is unreachable.')

    return [light_ids, light_names]

def turn_on_lights(light, name):
    """Send a state change to a single Hue light and report whether it succeeded."""
    url = f'http://{IP}/api/{USERNAME}/lights/{light}/state'

    # Hue state payload (JSON string)
    payload = "{\"on\":true}"
    headers = {}

    response = requests.request("PUT", url, headers=headers, data=payload)
    if response.json()[0]["success"].keys() == "/lights/{light}/state/on" and response[1].item() == "true":
        logger.info(f'{name} has been turned on.')
    else:
        logger.warning(f'{name} was not able to be turned on.')

def main():
    """Poll Verkada continuously, refreshing the auth token every ~30 minutes."""
    logger.info("Script starting....")
    # Time the current Verkada token was issued; used to decide when to refresh it
    auth_timer = 0
    while True:
        # Tokens last about 30 minutes; refresh just before expiry (1790s)
        if (time.time() - auth_timer) > 1790:
            auth_payload = auth()
            auth_timer = auth_payload[1]
            token = auth_payload[0]
            logger.info("Obtaining new auth token from Verkada.")
        poll_camera(token)
        time.sleep(1)

main()