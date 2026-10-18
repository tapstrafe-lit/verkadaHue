import requests, urllib3
import os
import time
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

urllib3.disable_warnings()

last_seen = 0

IP = os.getenv("HUE_IP")
USERNAME = os.getenv("HUE_USERNAME")

def auth():
    url = "https://api.verkada.com/token"

    headers = {
        "accept": "application/json",
        "x-api-key": os.getenv("VERKADA_API_KEY")
        }

    response = requests.post(url, headers=headers)
    response = response.text
    token = response.split('"')[3]

    return token

def poll_camera():
    token = auth()
    url = "https://api.verkada.com/cameras/v1/people/person_of_interest?page_size=1"
    headers = {
        "accept": "application/json",
        "x-verkada-auth": token
        }

    response = requests.get(url, headers=headers)
    response = response.json()
    poi = response["persons_of_interest"][0]
    person = poi["label"]

    last_seen = datetime.fromtimestamp(poi["last_seen"], tz=ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f'{person} was last seen at {last_seen}')

    if person == "Nate":
        for light, name in get_lights()[0]:
            turn_on_lights(light, name)

def get_lights():
    url = f'http://{IP}/api/{USERNAME}/lights'

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload).json()

    light_ids = []
    light_names = []

    for light_id, light in response.items():
        light_name = light["name"]
        if light["state"]["reachable"] == "true":
            light_ids.append(light_id)
            light_names.append(light_name)
            print(f'{light_name} is reachable.')
        else:
            print(f'{light_name} is unreachable.')

    return [light_ids, light_name]

def turn_on_lights(light, name):
    url = f'http://{IP}/api/{USERNAME}/lights/{light}/state'

    payload = "{\"off\":true}"
    headers = {}

    response = requests.request("PUT", url, headers=headers, data=payload)
    if response[1].key() == "/lights/{light}/state/on" and response[1].item() == "true":
        print(f'{name} has been turned on.')
    else:
        print(f'{name} was not able to be turned on.')

poll_camera()

def main():
    while True:
        if (time.time() - last_seen) > 1750:
            token = auth()
            print("Obtaining token from Verkada.")
        poll_camera(token)
        time.sleep(1)

