FROM python:3.10-alpine
RUN mkdir /pip_cache
RUN --mount=type=cache,target=pip_cache \
    pip install --cache-dir /pip_cache --upgrade pip
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/pip_cache \
    pip install --cache-dir /pip_cache -r requirements.txt
COPY regexes .
COPY LICENSE .
COPY pyproject.toml .
COPY setup.py .
COPY src/ src
RUN pip install -e .
ENTRYPOINT ["python", "-m", "log_parser"]
