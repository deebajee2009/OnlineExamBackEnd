# Stage 1: Build Python dependencies
FROM python:3.10.8-slim-bullseye as build-python

# Install build dependencies
RUN apt-get update && \
    apt-get install -y libpq-dev python3-dev gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY ./requirements.txt /app/
WORKDIR /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Stage 2: Final stage
FROM python:3.10.8-slim-bullseye

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y libpq-dev postgresql-client netcat && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set work directory and environment variables
WORKDIR /opt/app
ENV PYTHONPATH=${PYTHONPATH}:${PWD}

# Copy dependencies from build stage
COPY --from=build-python /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=build-python /usr/local/bin/ /usr/local/bin/

# Copy application files and scripts
COPY . .

RUN pip freeze
COPY ./scripts/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./scripts/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY ./scripts/startbeat /startbeat
RUN sed -i 's/\r$//g' /startbeat
RUN chmod +x /startbeat


ENTRYPOINT ["/entrypoint"]
