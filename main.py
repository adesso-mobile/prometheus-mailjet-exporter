import requests
from requests.auth import HTTPBasicAuth
import os
import yaml
from datetime import datetime, timedelta
from dateutil import relativedelta

MAILJET_API_BASE_URL = "https://api.mailjet.com/v3/REST"


def _mailjet_retrieve_statistics(
    public_api_key: str, private_api_key: str, start_ts: int, end_ts: int
):
    response = requests.get(
        url=f"{MAILJET_API_BASE_URL}/statcounters",
        params={
            "CounterSource": "APIKey",
            "CounterTiming": "Message",
            "CounterResolution": "Day",
            "FromTS": start_ts,
            "ToTS": end_ts,
        },
        auth=HTTPBasicAuth(public_api_key, private_api_key),
    )
    return response.json()


def get_total_sent_messages_between(
    public_api_key: str, private_api_key: str, start_ts: int, end_ts: int
):
    total = 0
    for data in _mailjet_retrieve_statistics(
        public_api_key=public_api_key,
        private_api_key=private_api_key,
        start_ts=start_ts,
        end_ts=end_ts,
    )["Data"]:
        total += data["Total"]

    return total


def get_config(config_path):
    with open(config_path, "r") as fp:
        return yaml.load(fp)


if __name__ == "__main__":
    mailjet_api_public_key = os.environ["MAILJET_API_PUBLIC_KEY"]
    mailjet_api_private_key = os.environ["MAILJET_API_PRIVATE_KEY"]
    mailjet_exporter_config_path = os.getenv(
        "MAILJET_EXPORTER_CONFIG_PATH", "/etc/prometheus-mailjet-exporter/config.yaml"
    )

    config = get_config(mailjet_exporter_config_path)
    start_dom = config["start_dom"]
    max_count = config["max_count"]

    now = datetime.now()

    start_payment_period = datetime.strptime(
        f"{start_dom}.{now.month}.{now.year}", "%d.%m.%Y"
    )
    if now.day < start_dom:
        start_payment_period -= relativedelta.relativedelta(months=1)

    end_payment_period = start_payment_period + relativedelta.relativedelta(months=1)


    print(start_payment_period, end_payment_period)

    print(
        get_total_sent_messages_between(
            mailjet_api_public_key,
            mailjet_api_private_key,
            int(start_payment_period.timestamp()),
            int(end_payment_period.timestamp()),
        )
    )
