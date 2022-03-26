#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import flask
import asfpy.messaging
import netaddr
import requests
import logging

"""Simple GHA Workflow Status Notifier"""


JOB_FAILED = """
[GitHub] [{job_repo}]: Workflow run "{job_name}" failed!
-- 
The GitHub Actions job "{job_name}" on {job_repo}.git has failed.
Run started by GitHub user {job_actor} (triggered by {job_trigger}).

Head commit for run:
{trigger_hash} / {trigger_author} <{trigger_email}>
{trigger_log}

Report URL: {job_url}

With regards,
GitHub Actions via GitBox
"""

JOB_SUCCEEDED = """
[GitHub] [{job_repo}]: Workflow run "{job_name}" succeeded again!
--
The GitHub Actions job "{job_name}" on {job_repo}.git has succeeded.
Run started by GitHub user {job_actor} (triggered by {job_trigger}).

Head commit for run:
{trigger_hash} / {trigger_author} <{trigger_email}>
{trigger_log}

Report URL: {job_url}

With regards,
GitHub Actions via GitBox
"""

jobs = {}


def get_recipient(repo):
    return "<gnomes@infra.apache.org>"  # Just gnomes for now!


def parse_payload(run):
    job_status = run.get("conclusion", "unknown")
    job_name = run.get("name", "???")
    job_url = run.get("html_url", "")
    job_id = run.get("workflow_id", "")
    job_repo = run.get("repository", {}).get("name", "infrastructure-unknown")
    job_actor = run.get("actor", {}).get("login", "github")
    job_trigger = run.get("triggering_actor", {}).get("login", "github[bot]")
    trigger_hash = run.get("head_commit", {}).get("id")
    trigger_log = run.get("head_commit", {}).get("message")
    trigger_author = run.get("head_commit", {}).get("author", {}).get("name", "??")
    trigger_email = run.get("head_commit", {}).get("author", {}).get("email", "??")
    recipient = get_recipient(job_repo)
    if job_id not in jobs:
        jobs[job_id] = job_status
    if job_status == "failure":  # Always notify on failure
        subject, text = JOB_FAILED.split("--", 1)
        subject = subject.format(**locals()).strip()
        text = text.format(**locals()).strip()
        asfpy.messaging.mail(
            sender="GitBox <git@apache.org>", recipient=recipient, subject=subject, message=text
        )
    elif jobs[job_id] != job_status and job_status == "succeess":  # Status change, notify!
        subject, text = JOB_SUCCEEDED.split("--", 1)
        subject = subject.format(**locals()).strip()
        text = text.format(**locals()).strip()
        asfpy.messaging.mail(
            sender="GitBox <git@apache.org>", recipient=recipient, subject=subject, message=text
        )
    jobs[job_id] = job_status
    print(job_repo, job_id, job_status)


def main():

    # Grab all GitHub WebHook IP ranges
    webhook_ips = requests.get("https://api.github.com/meta").json()["hooks"]
    allowed_ips = list()
    for ip in webhook_ips:
        allowed_ips.append(netaddr.IPNetwork(ip))

    # Init Flask...
    app = flask.Flask(__name__)

    @app.route("/hook", methods=["POST", "PUT"])
    def parse_request():
        this_ip = netaddr.IPAddress(flask.request.remote_addr)
        allowed = any(this_ip in ip for ip in allowed_ips)
        if not allowed:
            return "No content\n"
        content = flask.request.json
        act = content.get("action")
        if act == "completed" and "workflow_run" in content:
            parse_payload(content["workflow_run"])
        return "Delivered\n"

    # Disable werkzeug request logging to stdout
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    # Start up the app
    app.run(host="0.0.0.0", port=8083, debug=False)


if __name__ == "__main__":
    main()
