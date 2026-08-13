FROM linuxserver/code-server:latest

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV SHELL=/bin/bash
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    git \
    git-lfs \
    openssh-client \
    bash \
    zsh \
    vim \
    nano \
    less \
    jq \
    unzip \
    zip \
    tar \
    gzip \
    procps \
    iproute2 \
    iputils-ping \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g npm@latest \
    && npm install -g pnpm \
    && rm -rf /var/lib/apt/lists/*

# kubectl
RUN curl -fsSL -o /usr/local/bin/kubectl \
      https://dl.k8s.io/release/v1.34.3/bin/linux/amd64/kubectl \
    && chmod +x /usr/local/bin/kubectl

# Helm
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \
      | bash

# Docker CLI only.
# The daemon remains outside this container.
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

# Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Useful shell defaults
RUN printf '%s\n' \
    'export PATH="/usr/local/bin:$PATH"' \
    'export EDITOR=vim' \
    'export VISUAL=vim' \
    > /etc/profile.d/shopnltd-code.sh

# VS Code extensions
RUN mkdir -p /opt/code-server-extensions \
    && code-server --install-extension GitHub.vscode-pull-request-github \
    && code-server --install-extension eamodio.gitlens \
    && code-server --install-extension dbaeumer.vscode-eslint \
    && code-server --install-extension esbenp.prettier-vscode \
    && code-server --install-extension ms-python.python \
    && code-server --install-extension ms-python.vscode-pylance \
    && code-server --install-extension redhat.vscode-yaml \
    && code-server --install-extension ms-azuretools.vscode-docker \
    && code-server --install-extension ms-kubernetes-tools.vscode-kubernetes-tools \
    && code-server --install-extension Continue.continue \
    || true

USER abc
