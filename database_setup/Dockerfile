# PostgreSQL with pgvector extension
# This Dockerfile is for custom database initialization if needed
# By default, we use the pgvector/pgvector:pg16 image directly

FROM pgvector/pgvector:pg16

# Set environment variables
ENV POSTGRES_USER=finedu_admin
ENV POSTGRES_PASSWORD=finedu_admin_password
ENV POSTGRES_DB=postgres

# Copy initialization scripts
# These will be executed in alphabetical order
COPY ./db/init/*.sql /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# The entrypoint and cmd are inherited from the base image
