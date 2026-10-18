"""Publish bounded host/dependency metrics without customer or broker content."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'shared/scripts'))
from compose_config import compose_command
from diagnostics import service_status


def cpu_counters():
    values = [int(value) for value in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
    return sum(values[:8]), values[3] + values[4]


def host_metrics(data_directory, backup_directory):
    memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    total, idle = cpu_counters()
    time.sleep(1)
    next_total, next_idle = cpu_counters()
    completed = [path for path in backup_directory.glob('quantnest-*.tar.age.uploaded') if path.is_file() and not path.is_symlink()]
    age = time.time() - max((path.stat().st_mtime for path in completed), default=0)
    return {
        'disk_free_bytes': shutil.disk_usage(data_directory).free,
        'memory_available_bytes': int(memory['MemAvailable'].split()[0]) * 1024,
        'cpu_busy_pct': 100 * (1 - (next_idle - idle) / max(1, next_total - total)),
        'backup_upload_age_seconds': max(0, age),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--compartment-ocid', required=True)
    parser.add_argument('--instance-ocid', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    metrics = host_metrics(Path(os.environ['QUANTNEST_DATA_DIRECTORY']), Path(os.environ['QUANTNEST_BACKUP_DIRECTORY']))
    command = compose_command(root, 'public')
    # Full Django configuration checks run at deploy/operator diagnostics time.
    # The minute monitor uses container health and one bounded metrics command.
    healthy = service_status(root, 'public')['services_ready']
    metrics['deployment_ready'] = int(healthy)
    metrics['redis_persistence_ok'] = 1
    for service in ('redis', 'redis-runtime'):
        result = subprocess.run([*command, 'exec', '-T', service, 'redis-cli', 'INFO', 'persistence'], capture_output=True, text=True, timeout=15)
        info = dict(line.split(':', 1) for line in result.stdout.splitlines() if ':' in line and not line.startswith('#'))
        metrics['redis_persistence_ok'] &= int(result.returncode == 0 and info.get('aof_enabled') == '1' and info.get('aof_last_write_status') == 'ok' and info.get('rdb_last_bgsave_status') == 'ok')
    result = subprocess.run([*command, 'exec', '-T', 'api', 'python', 'manage.py', 'deployment_metrics'], capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        metrics.update(json.loads(result.stdout))
    else:
        metrics.update(database_ok=0, execution_workers_ok=0, outbox_oldest_seconds=3600, order_pending_idle_seconds=3600)
        metrics['deployment_ready'] = 0
    import oci
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    client = oci.monitoring.MonitoringClient({}, signer=signer, timeout=(5, 15), service_endpoint=f'https://telemetry-ingestion.{signer.region}.oraclecloud.com')
    now = datetime.now(timezone.utc)
    data = [oci.monitoring.models.MetricDataDetails(namespace='quantnest', compartment_id=args.compartment_ocid,
        name=name, dimensions={'instanceId': args.instance_ocid}, datapoints=[oci.monitoring.models.Datapoint(timestamp=now, value=value)]) for name, value in metrics.items()]
    response = client.post_metric_data(oci.monitoring.models.PostMetricDataDetails(metric_data=data))
    if response.data.failed_metrics_count:
        raise RuntimeError('Infrastructure metrics were not accepted')
    print(json.dumps({'healthy': bool(metrics['deployment_ready']), 'metric_count': len(data)}))
    if not metrics['deployment_ready']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
