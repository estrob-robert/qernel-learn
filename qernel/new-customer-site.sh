#!/bin/sh
# Qernel Learn: make a customer's site on estrob-course-1.
#
# Run on the server as root, from a copy of this file:
#   sh new-customer-site.sh <domain> "<customer name>" <logo file> [<icon file>]
#   sh new-customer-site.sh learn.heartmentality.no "Heart Mentality" /root/heart-logo.png /root/heart-icon.png
#
# The domain's A record must point at this server first, or Traefik cannot get
# its certificate. Then, in this order:
#   1. qernel/customer-email.py on the Windows machine adds the sender.
#   2. bench --site <domain> execute lms.qernel_site.integration_key, run by
#      Robert himself, gives what goes into Qernel's Qernel Learn card.
#   3. bench --site <domain> execute lms.qernel_site.invite --kwargs '{...}'
#      invites the first admin, once everything has been seen to work.
# Every step can run again.
set -eu

SITE=${1:?domain}
CUSTOMER=${2:?customer name}
LOGO=${3:?logo file}
ICON=${4:-}

cd /root
COMPOSE="docker compose -p estrob-course --env-file estrob-course.env -f estrob-course-compose.yml"

# An image build needs about 25 GB, and the database shares this disk.
FREE_GB=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
if [ "$FREE_GB" -lt 10 ]; then
	echo "Only ${FREE_GB} GB free on /. Clean old images first." >&2
	exit 1
fi
[ -f "$LOGO" ] || { echo "No logo file at $LOGO" >&2; exit 1; }
[ -z "$ICON" ] || [ -f "$ICON" ] || { echo "No icon file at $ICON" >&2; exit 1; }

# 1. The site. The Administrator password is random and kept nowhere: we work
#    through bench, and `bench --site <domain> set-admin-password` resets it.
if $COMPOSE exec -T backend test -d "sites/$SITE"; then
	echo "Site $SITE exists, configuring it again."
else
	# Passed by name (-e DBP), so the values never sit on a command line.
	DBP=$(sed -n 's/^DB_PASSWORD=//p' estrob-course.env)
	AP=$(openssl rand -hex 24)
	export DBP AP
	$COMPOSE exec -T -e DBP -e AP backend sh -c \
		'bench new-site "$1" --mariadb-user-host-login-scope="%" --db-root-password "$DBP" --admin-password "$AP" --install-app payments --install-app lms' \
		sh "$SITE"
	unset DBP AP
fi

# 2. Traefik routes the domain to the portal (the site is picked by host name).
#    NO_ROUTE=1 leaves it out, for a throwaway test site without a domain.
if [ "${NO_ROUTE:-0}" != 1 ] && ! grep -q "Host(\`$SITE\`)" estrob-course-compose.yml; then
	cp estrob-course-compose.yml "estrob-course-compose.yml.bak-$(date +%Y%m%d%H%M%S)"
	sed -i "s/^\(\s*traefik.http.routers.frontend-http.rule: .*\)$/\1 || Host(\`$SITE\`)/" estrob-course-compose.yml
	grep -q "Host(\`$SITE\`)" estrob-course-compose.yml || { echo "Could not add $SITE to the Traefik rule" >&2; exit 1; }
	$COMPOSE up -d
fi

# 3. Settings, branding, the lock and the integration user.
$COMPOSE cp "$LOGO" "backend:/tmp/$(basename "$LOGO")"
LOGO_IN=/tmp/$(basename "$LOGO")
ICON_IN=""
if [ -n "$ICON" ]; then
	$COMPOSE cp "$ICON" "backend:/tmp/$(basename "$ICON")"
	ICON_IN=/tmp/$(basename "$ICON")
fi
KWARGS=$(python3 -c 'import json,sys; print(json.dumps({"customer_name": sys.argv[1], "logo": sys.argv[2], "icon": sys.argv[3]}))' "$CUSTOMER" "$LOGO_IN" "$ICON_IN")
$COMPOSE exec -T backend bench --site "$SITE" execute lms.qernel_site.configure --kwargs "$KWARGS"
$COMPOSE exec -T backend bench --site "$SITE" backup >/dev/null
echo "Done: https://$SITE. Next: the sender (customer-email.py on Windows)."
