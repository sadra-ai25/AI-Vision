FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    unixodbc \
    unixodbc-dev
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && echo "[ODBC Driver 17 for SQL Server]\nDescription=Microsoft ODBC Driver 17 for SQL Server\nDriver=/opt/microsoft/msodbcsql17/lib64/libmsodbcsql-17.10.5.1.so.1\nUsageCount=1" >> /etc/odbcinst.ini
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./src /app/src
COPY .env .env
# ENV PYTHONPATH="${PYTHONPATH}:/app"
ENV PYTHONPATH="${PYTHONPATH}:/app/src"
CMD ["python", "/app/src/main.py"]

