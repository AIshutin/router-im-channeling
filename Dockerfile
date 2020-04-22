FROM python:3.7

#COPY requirements.txt /app/
COPY . /app/
RUN pip3 install -r /app/requirements.txt

#COPY senderlib /app/senderlib
#COPY main.py /app/

ENV PORT 8080

CMD cd /app/ && uvicorn channel_manager:app --host 0.0.0.0 --port $PORT
