FROM python:3.12-slim
WORKDIR /app
COPY platform/android-cloud/controller/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY platform/android-cloud/controller/main.py ./main.py
USER 10001
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
