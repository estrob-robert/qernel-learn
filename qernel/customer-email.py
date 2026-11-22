"""Qernel Learn: give a customer's site its sender.

Run on the Windows machine, where the AhaSend key lives (user environment
variables AHASEND_COURSE_KEY and AHASEND_ACCOUNT_ID):

    python qernel/customer-email.py <domain> <sender email> "<sender name>" [<reply-to>]
    python qernel/customer-email.py learn.heartmentality.no kurs@email.heartmentality.no "Heart Mentality" hei@heartmentality.no

The sender's domain only sends, so replies go to <reply-to>, an inbox the
customer reads.

It makes an SMTP credential in AhaSend, locked to the sender's domain, and
hands it straight to the site (lms.qernel_site.configure_email). AhaSend shows
the password once; it is never printed or written to disk here, and the file
it passes through in the container is removed on arrival. If the site does not
take it, the credential is deleted again, so no unused keys are left behind.
"""

import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.request

SERVER = "root@185.14.97.43"
COMPOSE = "cd /root && docker compose -p estrob-course"
API = "https://api.ahasend.com/v2/accounts/{account}"


def env(name):
	"""From the process, or from the user's saved environment: a shell started
	before the variable was set does not have it."""
	if os.environ.get(name):
		return os.environ[name]
	import winreg

	with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
		return winreg.QueryValueEx(key, name)[0]


def api(method, path, body=None):
	key = env("AHASEND_COURSE_KEY")
	account = env("AHASEND_ACCOUNT_ID")
	request = urllib.request.Request(
		API.format(account=account) + path,
		method=method,
		data=json.dumps(body).encode() if body is not None else None,
		headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
	)
	try:
		with urllib.request.urlopen(request, timeout=30) as response:
			return json.loads(response.read() or b"{}")
	except urllib.error.HTTPError as e:
		# AhaSend's error body names the problem and holds no secret.
		sys.exit(f"AhaSend {method} {path}: {e.code} {e.read()[:300]!r}")


def ssh(command, stdin=None):
	return subprocess.run(["ssh", SERVER, command], input=stdin, capture_output=True, text=True)


def main():
	if len(sys.argv) not in (4, 5):
		sys.exit(__doc__)
	site, sender, name = sys.argv[1], sys.argv[2].strip().lower(), sys.argv[3]
	reply_to = sys.argv[4].strip().lower() if len(sys.argv) == 5 else ""
	domain = sender.split("@", 1)[1]

	domains = api("GET", "/domains").get("data", [])
	match = [d for d in domains if d.get("domain") == domain]
	if not match:
		sys.exit(f"{domain} is not a domain in this AhaSend account.")
	if not match[0].get("dns_valid"):
		sys.exit(f"{domain} is in AhaSend, but its DNS is not verified.")
	if match[0].get("paused"):
		sys.exit(f"{domain} is paused in AhaSend: {match[0].get('pause_reason')}")

	credential = api(
		"POST", "/smtp-credentials", {"name": f"Qernel Learn {site}", "scope": "scoped", "domains": [domain]}
	)
	payload = json.dumps(
		{
			"email_id": sender,
			"sender_name": name,
			"login_id": credential["username"],
			"password": credential["password"],
			"reply_to": reply_to,
		}
	)
	del credential["password"]

	path = f"/tmp/qernel-email-{secrets.token_hex(8)}.json"
	write = ssh(f"{COMPOSE} exec -T backend sh -c 'umask 077; cat > {path}'", stdin=payload)
	save = None
	if write.returncode == 0:
		save = ssh(
			f"{COMPOSE} exec -T backend bench --site {site} execute lms.qernel_site.configure_email"
			f" --kwargs '{json.dumps({'secret_file': path})}'"
		)
	if write.returncode != 0 or save.returncode != 0:
		ssh(f"{COMPOSE} exec -T backend rm -f {path}")
		api("DELETE", f"/smtp-credentials/{credential['id']}")
		# Frappe's error output can quote the source line, never the payload.
		print((write.stderr if write.returncode else save.stdout + save.stderr)[-1500:])
		sys.exit("The site did not take the sender. The AhaSend credential was deleted again.")
	print(save.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
	main()
