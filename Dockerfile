# irwhois — https://github.com/Omidsp79/irwhois
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/Omidsp79/irwhois" \
      org.opencontainers.image.description="Check .ir domain availability via whois.nic.ir"

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY irwhois/ ./irwhois/
RUN pip install --no-cache-dir . && rm -rf /root/.cache

EXPOSE 8000
ENTRYPOINT ["irwhois"]
CMD ["--help"]
