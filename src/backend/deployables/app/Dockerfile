FROM python:3.14-slim
COPY src.backend.deployables.app/bin.pex /app/app.pex
USER nobody
ENV PEX_ROOT=/tmp/pex
ENTRYPOINT ["/app/app.pex"]
# Run `migrate` once per release, then `serve` on every replica.
CMD ["serve"]
