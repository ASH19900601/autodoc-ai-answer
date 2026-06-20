# Production image: Linux, Windows-independent.
FROM python:3.11-slim

WORKDIR /app

# System libs needed by some wheels at runtime (lxml/pymupdf are manylinux
# wheels, but keep fonts so inserted CJK text renders if you later embed).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY autodoc ./autodoc

RUN pip install --no-cache-dir .

EXPOSE 8000

# The web UI is a thin layer over the CLI; the container simply runs the CLI.
CMD ["autodoc", "serve", "--host", "0.0.0.0", "--port", "8000"]
