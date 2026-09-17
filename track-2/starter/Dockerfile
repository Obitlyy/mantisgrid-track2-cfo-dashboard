FROM python:3.12-slim
WORKDIR /work
COPY requirements.lock.txt /tmp/requirements.lock.txt
RUN pip install --no-cache-dir -r /tmp/requirements.lock.txt
COPY starter/ /work/
