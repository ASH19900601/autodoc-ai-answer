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

EXPOSE 7860

# HF Spaces / Render / Cloud Run inject the listen port. Default to 7860
# (Hugging Face Spaces default). The web UI is a thin layer over the CLI;
# the container simply runs the CLI, which reads $PORT.
ENV PORT=7860
CMD ["sh", "-c", "autodoc serve --host 0.0.0.0 --port ${PORT}"]
