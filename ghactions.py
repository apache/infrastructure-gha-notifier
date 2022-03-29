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
import yaml
import os
import time

"""Simple GHA Workflow Status Notifier"""


JOB_FAILED = open("templates/job_failed.txt").read()
JOB_SUCCEEDED = open("templates/job_fixed.txt").read()
JOB_STATUS_SUCCESS = "success"
JOB_STATUS_FAILURE = "failure"
REPO_ROOT = "/x1/repos/asf"
jobs = {}

def get_recipient(repo):
    yaml_path = os.path.join(REPO_ROOT, f"{repo}.git", "notifications.yaml")
    if time.time() > 1649016000 and os.path.exists(yaml_path):  # Only active after 3rd of april 2022
        yml = yaml.safe_load(open(yaml_path, "r").read())
        if "jobs" in yml:
            return yml["jobs"]
    elif time.time() < 1649016000:  # Not active after 3rd of april 2022
        try:
            resp = requests.get(f"https://gitbox.apache.org/x1/repos/asf/{repo}.git/notifications.yaml")
            if resp and resp.status_code == 200:
                yml = yaml.safe_load(resp.text)
                if "jobs" in yml:
                    return yml["jobs"]
        except:  # misc breakages, ignore - this isn't an important service.
            pass
    return None


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
    if not recipient:  # No address configured, skip!
        return f"[skipped] {job_repo} {job_id} {job_status}"
    if job_id not in jobs:
        jobs[job_id] = job_status
    if job_status == JOB_STATUS_FAILURE:  # Always notify on failure
        subject, text = JOB_FAILED.split("--", 1)
        subject = subject.format(**locals()).strip()
        text = text.format(**locals()).strip()
        asfpy.messaging.mail(
            sender="GitBox <git@apache.org>", recipient=recipient, subject=subject, message=text
        )
        jobs[job_id] = JOB_STATUS_FAILURE
    elif jobs[job_id] != job_status and job_status == JOB_STATUS_SUCCESS:  # Status change, notify!
        subject, text = JOB_SUCCEEDED.split("--", 1)
        subject = subject.format(**locals()).strip()
        text = text.format(**locals()).strip()
        asfpy.messaging.mail(
            sender="GitBox <git@apache.org>", recipient=recipient, subject=subject, message=text
        )
        jobs[job_id] = JOB_STATUS_SUCCESS
    return f"{job_repo} {job_id} {job_status}"


def main():

    # Grab all GitHub WebHook IP ranges
    webhook_ips = requests.get("https://api.github.com/meta").json()["hooks"]
    allowed_ips = [netaddr.IPNetwork(ip) for ip in webhook_ips]

    # Init Flask...
    app = flask.Flask(__name__)

    @app.route("/hook", methods=["POST", "PUT"])
    def parse_request():
        this_ip = netaddr.IPAddress(flask.request.headers.get("X-Forwarded-For") or flask.request.remote_addr)
        allowed = any(this_ip in ip for ip in allowed_ips)
        if not allowed:
            return "No content\n"
        content = flask.request.json
        act = content.get("action")
        if act == "completed" and "workflow_run" in content:
            logmsg = parse_payload(content["workflow_run"])
            log.log(level=logging.WARNING, msg=logmsg)
        return "Delivered\n"

    # Disable werkzeug request logging to stdout
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    # Start up the app
    app.run(host="127.0.0.1", port=8083, debug=False)


if __name__ == "__main__":
    main()
