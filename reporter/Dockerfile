FROM python:3.10
RUN mkdir /pip_cache
RUN --mount=type=cache,target=/pip_cache \
    pip install --cache-dir /pip_cache --upgrade pip
WORKDIR /app
COPY reporter/requirements.txt .
RUN --mount=type=cache,target=/pip_cache \
    pip install --cache-dir /pip_cache -r requirements.txt
COPY reporter/app.py .
COPY reporter/generate-protos.sh .
COPY events.proto .
RUN ./generate-protos.sh --proto-file events.proto --output-directory protos
ENTRYPOINT [ "python", "app.py" ]
