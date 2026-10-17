FROM python:3.14-slim
COPY src.deployables.backend/bin.pex /app/backend.pex
USER nobody
ENV PEX_ROOT=/tmp/pex
ENTRYPOINT ["/app/backend.pex"]
# Run `migrate` once per release, then `serve` on every replica.
CMD ["serve"]
