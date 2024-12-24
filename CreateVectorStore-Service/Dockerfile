FROM python:3.10
WORKDIR /App
COPY . /App
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
EXPOSE 8089
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8089"]
