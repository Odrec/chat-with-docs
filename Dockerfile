FROM python:3.12

# Update package lists and install poppler-utils
RUN apt-get update && apt-get install -y poppler-utils

EXPOSE 8501

COPY requirements.txt /kiwi/requirements.txt
RUN pip install --no-cache-dir -r /kiwi/requirements.txt

COPY . /kiwi
WORKDIR /kiwi

USER nobody
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
ENTRYPOINT [ "streamlit", "run", "start.py", "--server.port=8501", "--server.address=0.0.0.0"]
