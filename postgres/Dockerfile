FROM postgres:16

RUN apt-get update \
    && apt-get install -y --no-install-recommends pgbackrest \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/lib/pgbackrest /etc/pgbackrest /var/log/pgbackrest /var/lib/pgbackrest/lock /var/lib/pgbackrest/spool /tmp/pgbackrest \
    && chown -R postgres:postgres /var/lib/pgbackrest /etc/pgbackrest
