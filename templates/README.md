# GHA Notifier - Email Templates
This directory contains the email templates used for notifying projects of 
build status updates via email.

The templates consist of an email topic template (first line), 
followed by a double dash, `--`, 
and then finally the email body template.

If you wish to update the email template(s), please do so via a Pull Request.

You may use the following variables in the templates:

- `{job_repo}`: The repository name (sans the .git extension) that the job ran on
- `{job_name}`: The name of the GHA job that ran
- `{job_status}`: The status (success/failure) of the run
- `{job_url}`: The URL to the GHA summary for the run
- `{job_id}`: The unique ID of the job that ran
- `{job_actor}`: The actor (GitHub user) that (via commit or manual action) approved the job
- `{job_trigger}`: The actor (GitHub user) that triggered the job
- `{trigger_hash}`: The head commit in the repo when the job was triggered
- `{trigger_log}`: The log of the head commit when the job was triggered
- `{trigger_author}`: The author of the head commit when the job was triggered
- `{trigger_email}`: The email address of the author of the head commit when the job was triggered.
