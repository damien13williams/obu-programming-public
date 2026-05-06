FROM python:3.11-slim
RUN mkdir -p /ui
WORKDIR /ui

COPY /ui . 
COPY /config /ui/config
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 3000

CMD ["python", "app.py"]
