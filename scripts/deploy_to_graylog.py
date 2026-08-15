#!/usr/bin/env python3

import argparse
import sys

import requests


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def build_event_definition(rule_name, query):
    return {
        "title": rule_name,
        "description": "Managed by GitHub Actions from a Sigma detection rule",
        "priority": 2,
        "alert": True,

        "config": {
            "type": "aggregation-v1",
            "query": query,
            "query_parameters": [],
            "filters": [],
            "streams": [],
            "stream_categories": [],
            "group_by": [],
            "series": [],
            "conditions": None,

            # Search the previous 5 minutes
            "search_within_ms": 300000,

            # Run every 5 minutes
            "execute_every_ms": 300000,

            "use_cron_scheduling": False,
            "cron_expression": None,
            "cron_timezone": None,

            # Maximum events produced per execution
            "event_limit": 100,
        },

        "field_spec": {},
        "key_spec": [],

        "notification_settings": {
            "grace_period_ms": 0,
            "backlog_size": 0,
        },

        "notifications": [],
        "storage": [],

       

        
        "state": "ENABLED",
    }


def find_existing_definition(session, base_url, rule_name):
    url = f"{base_url}/api/events/definitions"

    response = session.get(
        url,
        params={
            "page": 1,
            "per_page": 200,
        },
        timeout=30,
    )

    if not response.ok:
        fail(
            f"Could not list Graylog event definitions. "
            f"HTTP {response.status_code}: {response.text}"
        )

    data = response.json()

    definitions = data.get("event_definitions", [])

    for definition in definitions:
        if definition.get("title") == rule_name:
            return definition

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Create or update a Graylog Event Definition"
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Graylog base URL, for example http://127.0.0.1:9000",
    )

    parser.add_argument(
        "--token",
        required=True,
        help="Graylog REST API token",
    )

    parser.add_argument(
        "--rule",
        required=True,
        help="Name of the detection rule",
    )

    parser.add_argument(
        "--query",
        required=True,
        help="Graylog/Lucene query generated from Sigma",
    )

    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    session = requests.Session()

    # Graylog API-token authentication:
    # username = token value
    # password = literal word "token"
    session.auth = (args.token, "token")

    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",

            # Required by Graylog for POST/PUT/DELETE requests
            "X-Requested-By": "github-detection-workflow",
        }
    )

    try:
        existing = find_existing_definition(
            session,
            base_url,
            args.rule,
        )

        new_definition = build_event_definition(
            args.rule,
            args.query,
        )

        if existing is None:
            print(
                f"Creating Graylog event definition: {args.rule}"
            )

            url = (
                f"{base_url}/api/events/definitions"
                "?schedule=true"
            )

            # Graylog's create endpoint expects the definition
            # inside an "entity" object.
            payload = {
                "entity": new_definition
            }

            response = session.post(
                url,
                json=payload,
                timeout=30,
            )

        else:
            definition_id = existing["id"]

            print(
                f"Updating existing Graylog event definition: "
                f"{args.rule}"
            )

            url = (
                f"{base_url}/api/events/definitions/"
                f"{definition_id}?schedule=true"
            )

            # Preserve the existing object's ID and server-managed
            # fields required for an update.
            updated_definition = existing.copy()

            updated_definition["title"] = (
                new_definition["title"]
            )

            updated_definition["description"] = (
                new_definition["description"]
            )

            updated_definition["priority"] = (
                new_definition["priority"]
            )

            updated_definition["alert"] = (
                new_definition["alert"]
            )

            updated_definition["config"] = (
                new_definition["config"]
            )

            

            updated_definition.pop("scheduler", None)

            response = session.put(
                url,
                json=updated_definition,
                timeout=30,
            )

        if not response.ok:
            fail(
                f"Graylog rejected the deployment. "
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        result = response.json()

        print("Graylog deployment succeeded.")
        print(f"Rule: {args.rule}")

        if result.get("id"):
            print(
                f"Event Definition ID: {result['id']}"
            )

    except requests.RequestException as error:
        fail(f"Graylog API request failed: {error}")


if __name__ == "__main__":
    main()