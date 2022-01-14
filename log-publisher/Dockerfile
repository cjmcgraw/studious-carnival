FROM python:3.10-alpine
RUN apk update && apk upgrade && apk add build-base g++ linux-headers bash coreutils busybox-extras
RUN mkdir /pip_cache
RUN --mount=type=cache,target=pip_cache \
    pip install --cache-dir /pip_cache --upgrade pip
WORKDIR /app
COPY log-publisher/requirements.txt .
RUN --mount=type=cache,target=/pip_cache \
    pip install --cache-dir /pip_cache -r requirements.txt
COPY log-publisher/regexes regexes
COPY log-publisher/LICENSE .
COPY log-publisher/pyproject.toml .
COPY log-publisher/setup.py .
COPY log-publisher/src/ src
COPY log-publisher/generate-protos.sh .
COPY events.proto .
RUN ./generate-protos.sh --proto-file events.proto --output-directory src/log_publisher/protos
RUN pip install -e .
RUN ls -alR
ENTRYPOINT ["python", "-m", "log_publisher"]
