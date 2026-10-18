#!/usr/bin/env bash
set -euo pipefail
# Usage: sudo bash infra/public/scripts/bootstrap_host.sh /mnt/quantnest-data /opt/quantnest/current
# The data volume must already be verified, formatted and mounted by the operator.
data_root=${1:?Pass the existing data-volume mount}
release_root=${2:?Pass the reviewed release directory}
[[ $(id -u) == 0 ]] || { echo 'Run as root'; exit 1; }
[[ "$data_root" = /* && "$release_root" = /* && "$data_root" != / ]] || { echo 'Pass absolute data and release paths; the data mount cannot be /'; exit 1; }
[[ "$data_root" != *[[:space:]]* ]] || { echo 'Use a data mount path without whitespace'; exit 1; }
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo 'This bootstrap supports Ubuntu 24.04 (Python 3.12)'; exit 1; }
mountpoint -q "$data_root" || { echo 'Data directory must be an existing mounted volume'; exit 1; }
[[ -f "$release_root/infra/public/requirements.lock" ]] || { echo 'Release is missing the operations lockfile'; exit 1; }
if [[ -d /var/lib/docker ]] && find /var/lib/docker -mindepth 1 -print -quit | grep -q .; then
  echo 'This bootstrap requires a fresh Docker host. Migrate existing Docker data in a reviewed maintenance window.'; exit 1
fi
apt-get update
apt-get install -y docker.io docker-compose-v2 python3-venv age
id quantnest >/dev/null 2>&1 || useradd --system --create-home --home-dir /opt/quantnest --shell /usr/sbin/nologin quantnest
usermod -aG docker quantnest
install -d -m 700 -o quantnest -g quantnest /etc/quantnest "$data_root/backups" /opt/quantnest/operations
install -d -m 711 "$data_root/docker" /etc/docker
python3 - "$data_root/docker" <<'PY'
import json, pathlib, sys
path = pathlib.Path('/etc/docker/daemon.json')
config = json.loads(path.read_text()) if path.exists() else {}
config['data-root'] = sys.argv[1]
config['log-driver'] = 'json-file'
config['log-opts'] = {'max-size': '10m', 'max-file': '3'}
path.write_text(json.dumps(config, indent=2) + '\n')
PY
install -d -m 755 /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/quantnest-storage.conf <<EOF
[Unit]
RequiresMountsFor=$data_root
ConditionPathIsMountPoint=$data_root
EOF
python3 -m venv /opt/quantnest/operations
/opt/quantnest/operations/bin/pip install --require-hashes -r "$release_root/infra/public/requirements.lock"
install -m 644 "$release_root"/infra/public/systemd/* /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now docker
systemctl restart docker
echo 'Configure protected app and operations environment files, deploy, then enable the backup and monitoring timers.'
