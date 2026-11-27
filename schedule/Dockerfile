FROM python:3.12-slim

WORKDIR /app

# copy the requirements file in the workdir
COPY requirements.txt /app/

# install the Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# copy the app files and directories
COPY schedule/ /app/

# start schedule.py when the container is started
CMD ["python", "-u", "schedule.py"]
