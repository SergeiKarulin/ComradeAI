FROM python:3.8
#Need to build on such docker https://cloud.google.com/sdk/docs/downloads-docker / gcr.io/google.com/cloudsdktool/google-cloud-cli:latest
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
CMD [ "python", "./agent.py" ]