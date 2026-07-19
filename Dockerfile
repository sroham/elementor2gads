FROM python:3.13-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY elementor2gads ./elementor2gads
RUN python -m pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

FROM python:3.13-slim

LABEL org.opencontainers.image.title="elementor2gads" \
      org.opencontainers.image.description="Local Elementor to Google Ads Customer Match CSV converter" \
      org.opencontainers.image.vendor="Elasyn" \
      org.opencontainers.image.url="https://elasyn.com.au" \
      org.opencontainers.image.licenses="MIT"

RUN useradd --create-home --uid 10001 appuser
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

WORKDIR /work
USER appuser
ENTRYPOINT ["elementor2gads"]
