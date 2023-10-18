FROM python:3.8
WORKDIR /app
COPY requirements.txt docker_exporter.py  ./ 
RUN pip install --no-cache-dir -r requirements.txt
CMD [ "python", "./docker_exporter.py" ]
