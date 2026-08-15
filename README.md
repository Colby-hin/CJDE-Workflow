# Automated Sigma Detection Deployment to Graylog

## Overview

This project is a Detection as Code lab using Sigma, GitHub Actions, Python, Docker, and Graylog.

The goal was to automate the process of taking a Sigma rule from GitHub and turning it into a working Graylog Event Definition.

Instead of rebuilding detections manually inside Graylog, I can write a Sigma rule, push it to GitHub, and let the workflow validate, convert, and deploy it.

## Workflow

```text
Sigma Rule
    ↓
Git Push
    ↓
GitHub Actions
    ↓
Sigma Validation
    ↓
Graylog Field Mapping
    ↓
Lucene Conversion
    ↓
Self Hosted Runner
    ↓
Graylog REST API
    ↓
Event Definition
    ↓
Alert
```

## How It Works

Sigma rules are stored in the `rules` folder.

GitHub Actions validates the rules before deployment.

A custom Sigma pipeline maps generic Sigma fields such as `Image` and `CommandLine` to Graylog fields such as `process_path` and `process_command_line`.

The rule is then converted into a Lucene query.

A self hosted GitHub runner on my Kali laptop runs the deployment job because Graylog is hosted locally.

A Python script sends the converted detection to the Graylog REST API.

If the Event Definition does not exist, it is created.

If it already exists, it is updated.

## Detections

### Certutil Download

The first rule detects suspicious use of `certutil.exe` with a web address and the `urlcache` option.

The logic is:

```text
certutil.exe is running

AND

The command line contains HTTP or HTTPS

AND

The command line contains urlcache
```

I tested this rule by sending controlled process telemetry into Graylog through a GELF HTTP input.

The event matched the generated query and Graylog successfully created an alert for `certutil_download_windows`.

This confirmed that the complete workflow worked from Sigma rule to Graylog alert.

### PowerShell Encoded Command

I created a second rule for PowerShell encoded command usage.

The rule checks for PowerShell or PowerShell Core and looks for `EncodedCommand` or `enc` in the command line.

I generated a new UUID, wrote the Sigma rule, committed it, and pushed it to GitHub.

The GitHub Actions workflow completed successfully and Graylog automatically created the `powershell_encoded_command` Event Definition.

## What I Verified

1. Sigma rules were stored and versioned in Git.

2. GitHub Actions validated the rules successfully.

3. Sigma converted the rules into Lucene queries.

4. Graylog field mappings were applied correctly.

5. The self hosted runner reached the local Graylog instance.

6. The Python script deployed detections through the Graylog REST API.

7. Graylog automatically created Event Definitions.

8. Controlled test telemetry was ingested successfully.

9. The Certutil rule matched the test event.

10. Graylog generated a real Certutil alert.

11. The PowerShell rule was created manually and deployed successfully.

