import time
import docker
import subprocess
import re
from datetime import datetime, timedelta
from prometheus_client import start_http_server, Gauge, REGISTRY

# Unregister the default Python garbage collector metric from Prometheus
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])
unwanted_metrics = [
    'python_info',
    'process_virtual_memory_bytes',
    'process_resident_memory_bytes',
    'process_start_time_seconds',
    'process_cpu_seconds_total',
    'process_open_fds',
    'process_max_fds'
]
for metric_name in unwanted_metrics:
    if metric_name in REGISTRY._names_to_collectors:
        REGISTRY.unregister(REGISTRY._names_to_collectors[metric_name])

def get_container_info(container):
    try:
        # Get the attributes and name of the container
        container_info = container.attrs
        container_name = container.name
        return container_info, container_name
    except Exception as e:
        # Return None if there is an exception
        return None, None

def update_prometheus_metrics(container_name, container_state, uptime_seconds, restarted_within_minute, error_count, warning_count, critical_count=0):
    # Update the container status metric based on the container state
    container_status.labels(container_name, container_state).set(1 if container_state == 'running' else 0)
    # Update the container restart count metric
    container_restart_count.labels(container_name).set(int(restarted_within_minute))
    # Update the container uptime metric
    container_uptime_seconds.labels(container_name).set(uptime_seconds)
    # Update the container log count metrics for different log levels
    container_log_count.labels(container_name, 'error').set(error_count)
    container_log_count.labels(container_name, 'warning').set(warning_count)
    container_log_count.labels(container_name, 'critical').set(critical_count)

def monitor_containers():
    # Create a Docker client
    client = docker.from_env()
    # Get a list of all containers
    containers = client.containers.list()

    for container in containers:
        # Get the container information and name
        container_info, container_name = get_container_info(container)
        if container_info is None:
            # Skip to the next container if there is no information available
            continue

        # Get the container state and calculate the uptime in seconds
        container_state = container_info['State']['Status']
        uptime = container_info['State']['StartedAt']
        uptime = uptime[:19]
        uptime_seconds = (datetime.utcnow() - datetime.fromisoformat(uptime)).total_seconds()

        # Get the time of the last restart and check if it occurred within the last minute
        last_restart = container_info['State']['FinishedAt']
        last_restart = last_restart[:19]
        restarted_within_minute = (datetime.utcnow() - datetime.fromisoformat(last_restart)) < timedelta(minutes=10)

        # Get the container logs and count the occurrences of different log levels
        logs = container.logs().decode('utf-8')
        error_count = logs.count('ERROR')
        warning_count = logs.count('WARNING')
        critical_count = logs.count('CRITICAL')

        # Update the Prometheus metrics for the container
        update_prometheus_metrics(container_name, container_state, uptime_seconds, restarted_within_minute, error_count, warning_count, critical_count)


# Define Prometheus metrics
container_status = Gauge('container_status', 'Статус контейнера (0 - "status != running", 1 - "status = running")', ['container_name', 'status'])
container_restart_count = Gauge('container_restart_count', 'Контейнер перезапускался в течение последней минуты (0 - нет, 1 - да)', ['container_name'])
container_uptime_seconds = Gauge('container_uptime_seconds', 'Время работы контейнера в секундах', ['container_name'])
container_log_count = Gauge('container_log_count', 'Количество логов контейнера по уровню (error, warning, critical)', ['container_name', 'log_level'])

if __name__ == '__main__':
    # Start the HTTP server for Prometheus on port 1624
    start_http_server(1624)

    while True:
        # Monitor the containers and update the metrics
        monitor_containers()
        # Sleep for 5 seconds before monitoring again
        time.sleep(5)
