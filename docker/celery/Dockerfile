ARG python_version
FROM python:${python_version}-stretch

# Install required software.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libmemcached-dev \
        nodejs \
        postgresql-client-9.6 \
        postgresql-server-dev-9.6 \
        yarn \
    # Clean up what can be cleaned up.
    && apt-get autoremove -y
WORKDIR /app

# Install Pontoon Python requirements
COPY requirements/* /app/requirements/

RUN pip install -U 'pip>=8' && \
    pip install --no-cache-dir --require-hashes -r requirements/dev.txt

# Create the app user
RUN groupadd -r --gid=1000 pontoon && useradd --no-log-init -r -m -g pontoon pontoon
RUN chown -R pontoon:pontoon /app
USER pontoon
