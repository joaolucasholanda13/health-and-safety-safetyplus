#!/usr/bin/env bash
set -Eeuo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo 'Execute com sudo.' >&2
  exit 1
fi
cd /opt/safety-plus
python3 -m py_compile tools/maintenance.py
for name in safetyplus-monitor.service safetyplus-monitor.timer safetyplus-backup.service safetyplus-backup.timer safetyplus-tests.service safetyplus-tests.timer; do
  install -m 644 "ops/maintenance/$name" "/etc/systemd/system/$name"
done
if [ ! -f /etc/safetyplus-maintenance.conf ]; then
  install -m 600 /dev/null /etc/safetyplus-maintenance.conf
  cat > /etc/safetyplus-maintenance.conf <<'CONFIG'
MAINTENANCE_AUTO_RESTART=0
MAINTENANCE_HEALTH_URL=https://safetyplus.tech/health
CONFIG
fi
install -d -m 700 /var/lib/safetyplus-maintenance
install -d -m 755 /var/lib/safetyplus-maintenance/public
systemctl daemon-reload
systemctl enable --now safetyplus-monitor.timer safetyplus-backup.timer safetyplus-tests.timer
systemctl list-timers safetyplus-monitor.timer safetyplus-backup.timer safetyplus-tests.timer
