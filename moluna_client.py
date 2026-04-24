import requests


def send_order_to_moluna(payload):

    url = "https://api.buchbutler.de/ORDER/"

    response = requests.post(url, json=payload)

    print("Moluna Antwort:", response.text)

    return response.json()
