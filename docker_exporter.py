import time
import docker
import subprocess
import re
from datetime import datetime, timedelta 
from prometheus_client import start_http_server, Gauge, REGISTRY, generate_latest
from http.server import BaseHTTPRequestHandler, HTTPServer

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

def update_prometheus_metrics(container_name, container_state, uptime_seconds, restarted_within_minute):
    # Update the container status metric based on the container state
    container_status.labels(container_name, container_state).set(1 if container_state == 'running' else 0)
    # Update the container restart count metric
    container_restart_count.labels(container_name).set(int(restarted_within_minute))
    # Update the container uptime metric
    container_uptime_seconds.labels(container_name).set(uptime_seconds)

# Define Prometheus metrics
container_status = Gauge('container_status', 'Container status (0 - "status != running", 1 - "status = running")', ['container_name', 'status'])
container_restart_count = Gauge('container_restart_count', 'Container restart count within the last minute (0 - no, 1 - yes)', ['container_name'])
container_uptime_seconds = Gauge('container_uptime_seconds', 'Container uptime in seconds', ['container_name'])

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
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
                restarted_within_minute = (datetime.utcnow() - datetime.fromisoformat(last_restart)) < timedelta(minutes=1)

                # Update the Prometheus metrics for the container
                update_prometheus_metrics(container_name, container_state, uptime_seconds, restarted_within_minute)

            # Generate the Prometheus output
            output = generate_latest()

            # Send the response with the Prometheus output
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(output)

        else:
            # Send a 404 error for all other requests
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'404 Not Found')

if __name__ == '__main__':
    # Start the Prometheus HTTP server with the custom request handler
    server = HTTPServer(('0.0.0.0', 1624), RequestHandler)
    server.serve_forever()
