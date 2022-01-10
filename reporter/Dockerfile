FROM python:3.10
RUN mkdir /pip_cache
RUN --mount=type=cache,target=/pip_cache \
    pip install --cache-dir /pip_cache --upgrade pip
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/pip_cache \
    pip install --cache-dir /pip_cache -r requirements.txt
COPY app.py .
ENTRYPOINT [ "python", "app.py" ]
