FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    libfreetype6 \
    libpng16-16 \
    ffmpeg \
    ca-certificates \
    curl \
    gettext-base \
    git \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        "sphinx>=7.2,<9" \
        "myst-parser>=2.0,<5" \
        "sphinx-rtd-theme>=3.0" \
        "sphinxcontrib-mermaid>=0.9"\
        "numpy==2.3.2"\
        "matplotlib==3.10.5"


ENV HOME=/root

# Installer Claude Code via npm (le plus fiable en Docker)
RUN npm install -g @anthropic-ai/claude-code

# Configurer le PATH pour les shells interactifs
RUN echo 'export PATH="/root/.local/bin:$PATH"' >> /root/.bashrc

CMD ["/bin/bash"]