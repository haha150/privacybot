FROM python:3.11-slim
RUN mkdir /app
ADD . /app 
WORKDIR /app
RUN pip3 install -r requirements.txt
CMD ["python", "main.py"]