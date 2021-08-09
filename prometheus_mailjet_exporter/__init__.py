import requests
from requests.auth import HTTPBasicAuth
import os
import yaml
from datetime import datetime, timedelta
from dateutil import relativedelta
import prometheus_client
import time

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
            "Limit": 31,
        },
        auth=HTTPBasicAuth(public_api_key, private_api_key),
    )
    return response.json()


def get_total_sent_messages_between(
    public_api_key: str, private_api_key: str, start_ts: int, end_ts: int,
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


def run():
    try:
        interval = os.getenv("MAILJET_EXPORTER_INTERVAL_SEC", 60)

        port = os.getenv("MAILJET_EXPORTER_PORT", 9310)
        prometheus_client.start_http_server(port)

        mailjet_api_public_key = os.environ["MAILJET_API_PUBLIC_KEY"]
        mailjet_api_private_key = os.environ["MAILJET_API_PRIVATE_KEY"]
        mailjet_exporter_config_path = os.getenv(
            "MAILJET_EXPORTER_CONFIG_PATH", "/etc/prometheus-mailjet-exporter/config.yaml"
        )

        mailjet_max_mail_sent_count_gauge = prometheus_client.Gauge(
            "mailjet_max_mail_sent_count", "desc", []
        )
        mailjet_current_mail_sent_count_gauge = prometheus_client.Gauge(
            "mailjet_current_mail_sent_count", "desc", []
        )

        config = get_config(mailjet_exporter_config_path)
        start_dom = config["start_dom"]
        max_count = config["max_count"]

        mailjet_max_mail_sent_count_gauge.set(max_count)

        while True:
            start_time = time.time()
            now = datetime.now()

            start_payment_period = datetime.strptime(
                f"{start_dom}.{now.month}.{now.year}", "%d.%m.%Y"
            )
            if now.day < start_dom:
                start_payment_period -= relativedelta.relativedelta(months=1)

            end_payment_period = start_payment_period + relativedelta.relativedelta(months=1)

            mailjet_current_mail_sent_count_gauge.set(
                get_total_sent_messages_between(
                    mailjet_api_public_key,
                    mailjet_api_private_key,
                    int(start_payment_period.timestamp()),
                    int(end_payment_period.timestamp()),
                )
            )

            while start_time + interval > time.time():
                time.sleep(1)

    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    run()
