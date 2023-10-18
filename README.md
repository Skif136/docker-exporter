# Installation and Usage
The docker_exporter listens on HTTP port 1624 by default.
##### Docker
For Docker run.
```
sudo docker run -d \
--name my_docker_exporter \
-p 1624:1624 -v /var/run/docker.sock:/var/run/docker.sock\
docker_exporter 
```
##### Metrics
This exporter will export the following metrics.

- container_status (Container status (0 - "status != running", 1 - "status = running"))
- container_restart_count (The container was restarted within the last minute (0 - no, 1 - yes))
- container_uptime_seconds (Container operating time in seconds)
- container_log_count (Number of container logs by level (error, warning, critical))
##### Development building and running

###### Build
```
git clone https://github.com/Skif136/docker-exporter.git
cd docker_exporter
sudo docker build -t docker_exporter .
```
###### Run
```
sudo docker run -d \
--name my_docker_exporter \
-p 1624:1624 -v /var/run/docker.sock:/var/run/docker.sock\
docker_exporter 
```
