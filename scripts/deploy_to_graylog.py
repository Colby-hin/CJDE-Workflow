#!/usr/bin/env python3

import argparse
import sys

import requests


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def sigma_level_to_graylog_priority(level):
    level = level.lower().strip()

    mapping = {
        "informational": 1,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 3,
    }

    return mapping.get(level, 2)


def build_event_definition(rule_name, query, level):
    priority = sigma_level_to_graylog_priority(level)

    return {
        "title": rule_name,
        "description": "Managed by GitHub Actions from a Sigma detection rule",
        "priority": priority,
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


def main():
    parser = argparse.ArgumentParser(
        description="Create or update a Graylog Event Definition"
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Graylog base URL",
    )

    parser.add_argument(
        "--token",
        required=True,
        help="Graylog API token",
    )

    parser.add_argument(
        "--rule",
        required=True,
        help="Rule name",
    )

    parser.add_argument(
        "--query",
        required=True,
        help="Graylog Lucene query",
    )

    parser.add_argument(
        "--level",
        default="medium",
        help="Sigma severity level",
    )

    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    session = requests.Session()

    session.auth = (
        args.token,
        "token",
    )

    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-By": "github-actions",
        }
    )

    priority = sigma_level_to_graylog_priority(args.level)

    print(
        f"Sigma severity: {args.level} "
        f"-> Graylog priority: {priority}"
    )

    new_definition = build_event_definition(
        args.rule,
        args.query,
        args.level,
    )

    response = session.get(
        f"{base_url}/api/events/definitions",
        params={
            "page": 1,
            "per_page": 200,
        },
        timeout=30,
    )

    if not response.ok:
        fail(
            f"Could not retrieve Graylog event definitions: "
            f"{response.status_code} {response.text}"
        )

    payload = response.json()

    definitions = payload.get(
        "event_definitions",
        payload.get("definitions", []),
    )

    existing = None

    for definition in definitions:
        if definition.get("title") == args.rule:
            existing = definition
            break

    if existing is None:
        print(
            f"Creating new Graylog event definition: "
            f"{args.rule}"
        )

        response = session.post(
            f"{base_url}/api/events/definitions?schedule=true",
            json={
                "entity": new_definition,
            },
            timeout=30,
        )

        if not response.ok:
            fail(
                f"Graylog create failed: "
                f"{response.status_code} {response.text}"
            )

        print(
            f"Created Graylog event definition: "
            f"{args.rule}"
        )

        return

    definition_id = existing.get("id")

    if not definition_id:
        fail(
            "Existing Graylog event definition "
            "does not contain an ID"
        )

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
            f"Graylog update failed: "
            f"{response.status_code} {response.text}"
        )

    print(
        f"Updated Graylog event definition: "
        f"{args.rule}"
    )


if __name__ == "__main__":
    main()