#!/usr/bin/env python3

import argparse
import sys
from urllib.parse import quote

import requests
import urllib3


# The course lab may use a self-signed Splunk certificate.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main():
    parser = argparse.ArgumentParser(
        description="Deploy a converted Sigma rule to Splunk"
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Splunk management URL"
    )

    parser.add_argument(
        "--token",
        required=True,
        help="Splunk authentication token"
    )

    parser.add_argument(
        "--rule",
        required=True,
        help="Name of the Splunk rule / saved search"
    )

    parser.add_argument(
        "--query",
        required=True,
        help="Splunk SPL query"
    )

    parser.add_argument(
        "--actions",
        default="log",
        help="Alert actions"
    )

    args = parser.parse_args()

    splunk_url = args.url.rstrip("/")

    headers = {
        "Authorization": f"Bearer {args.token}"
    }

    # Splunk saved-search REST endpoint
    saved_searches_url = (
        f"{splunk_url}/servicesNS/nobody/search/saved/searches"
    )

    encoded_rule_name = quote(args.rule, safe="")
    existing_rule_url = (
        f"{saved_searches_url}/{encoded_rule_name}"
    )

    rule_settings = {
        "search": args.query,
        "is_scheduled": "1",
        "cron_schedule": "*/5 * * * *",
        "dispatch.earliest_time": "-5m",
        "dispatch.latest_time": "now",
        "alert_type": "number of events",
        "alert_comparator": "greater than",
        "alert_threshold": "0",
        "alert.track": "1",
        "disabled": "0",
    }

    try:
        print(f"Checking for existing rule: {args.rule}")

        check_response = requests.get(
            existing_rule_url,
            headers=headers,
            params={"output_mode": "json"},
            verify=False,
            timeout=30,
        )

        if check_response.status_code == 200:
            print(f"Rule exists. Updating: {args.rule}")

            response = requests.post(
                existing_rule_url,
                headers=headers,
                data=rule_settings,
                params={"output_mode": "json"},
                verify=False,
                timeout=30,
            )

        elif check_response.status_code == 404:
            print(f"Rule does not exist. Creating: {args.rule}")

            create_settings = {
                "name": args.rule,
                **rule_settings,
            }

            response = requests.post(
                saved_searches_url,
                headers=headers,
                data=create_settings,
                params={"output_mode": "json"},
                verify=False,
                timeout=30,
            )

        else:
            print("Unable to check whether the rule exists.")
            print(f"HTTP status: {check_response.status_code}")
            print(check_response.text)
            sys.exit(1)

        if response.ok:
            print(f"Successfully deployed rule: {args.rule}")
            sys.exit(0)

        print(f"Failed to deploy rule: {args.rule}")
        print(f"HTTP status: {response.status_code}")
        print(response.text)
        sys.exit(1)

    except requests.RequestException as error:
        print(f"Error communicating with Splunk: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()