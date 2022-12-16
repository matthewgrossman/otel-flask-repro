FROM python:3.8-slim
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt
COPY . /app
ENTRYPOINT ["flask", "run", "--host=0.0.0.0", "--port=8080"]
