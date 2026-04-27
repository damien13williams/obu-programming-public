FROM python:3.11-slim
RUN mkdir -p /ui
WORKDIR /ui

COPY /ui . 
RUN pip install --no-cache-dir -r requirements.txt


CMD ["python", "app.py"]