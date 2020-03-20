FROM python:3.7

COPY requirements.txt /app/
RUN pip3 install -r /app/requirements.txt

COPY senderlib /app/senderlib
COPY main.py /app/

CMD cd /app/ && uvicorn main:app --reload --port 2000
