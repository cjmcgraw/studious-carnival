FROM rabbitmq:3.9-management-alpine
RUN apk update && apk upgrade && apk add python3-dev py3-pip build-base g++ linux-headers bash coreutils busybox-extras
RUN ln -s $(which python3) /usr/bin/python
RUN python --version
RUN mkdir /pip_cache
WORKDIR /app
ENV PATH ${PATH}:/app:/var/lib/rabbitmq/.local/bin
COPY rabbitmq/requirements.txt .
RUN --mount=type=cache,target=/pip_cache \
    pip install --cache-dir /pip_cache --user --upgrade pip && \
    pip install --cache-dir /pip_cache --user -r requirements.txt
COPY rabbitmq/read-from-exchange.py .
COPY rabbitmq/write-to-exchange.py .
COPY rabbitmq/generate-protos.sh .
COPY events.proto .
RUN ./generate-protos.sh --proto-file events.proto --output-directory protos
