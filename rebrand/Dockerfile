# rebrand/Dockerfile
#
# Single image for both the APK and EXE rebrand jobs. Built once per
# workflow run (or cached) so we can run apktool, apksigner, aapt2,
# zipalign, makensis, and osslsigncode from one container.
#
# Tag convention: ghcr.io/<org>/rebrand-toolchain:<sha>

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# ---------------------------------------------------------------------------
# OS packages
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    ca-certificates-java \
    wget curl unzip git 7zip file gnupg2 \
    build-essential libz-dev liblzma-dev \
    python3 python3-pip python3-yaml python3-pil \
    libcairo2 librsvg2-bin \
    autoconf automake libtool pkg-config gettext \
    nsis \
    mingw-w64 mingw-w64-tools \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Android command-line tools (apktool, build-tools, platform-tools)
#
# We pin specific versions so the build is reproducible.
#   - apktool 2.9.3 (apktool.jar)
#   - build-tools 34.0.0  (apksigner, aapt2, zipalign)
#   - platform  android-34
# ---------------------------------------------------------------------------
ARG ANDROID_SDK_VERSION=11076708
ARG ANDROID_PLATFORM=android-34
ARG ANDROID_BUILD_TOOLS=34.0.0
ARG APKTOOL_VERSION=2.9.3

ENV ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

RUN mkdir -p "${ANDROID_HOME}/cmdline-tools" \
    && cd /tmp \
    && wget -q "https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_SDK_VERSION}_latest.zip" -O cmdline-tools.zip \
    && unzip -q cmdline-tools.zip -d "${ANDROID_HOME}/cmdline-tools" \
    && mv "${ANDROID_HOME}/cmdline-tools/cmdline-tools" "${ANDROID_HOME}/cmdline-tools/latest" \
    && rm cmdline-tools.zip \
    && yes | "${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null \
    && "${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager" \
        "platform-tools" \
        "platforms;${ANDROID_PLATFORM}" \
        "build-tools;${ANDROID_BUILD_TOOLS}" \
    && rm -rf "${ANDROID_HOME}/.android" /root/.android

ENV PATH="${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/build-tools/${ANDROID_BUILD_TOOLS}"

# apktool — small wrapper script around the jar
RUN mkdir -p /opt/apktool \
    && curl -fsSL "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_${APKTOOL_VERSION}.jar" \
       -o /opt/apktool/apktool.jar \
    && cat >/usr/local/bin/apktool <<'EOF'
#!/bin/sh
exec java -jar /opt/apktool/apktool.jar "$@"
EOF
RUN chmod +x /usr/local/bin/apktool

# ---------------------------------------------------------------------------
# osslsigncode (built from source — the apt version is ancient and
# doesn't support SHA256 timestamping reliably)
# ---------------------------------------------------------------------------
ARG OSSLSIGNCODE_VERSION=2.7
RUN cd /tmp \
    && wget -q "https://github.com/mtrojnar/osslsigncode/releases/download/${OSSLSIGNCODE_VERSION}/osslsigncode-${OSSLSIGNCODE_VERSION}.tar.gz" \
    && tar xf "osslsigncode-${OSSLSIGNCODE_VERSION}.tar.gz" \
    && cd "osslsigncode-${OSSLSIGNCODE_VERSION}" \
    && ./configure --prefix=/usr/local --disable-dependency-tracking \
    && make -j"$(nproc)" \
    && make install \
    && cd /tmp && rm -rf "osslsigncode-${OSSLSIGNCODE_VERSION}"*

# ---------------------------------------------------------------------------
# Python deps for the overlay scripts
# ---------------------------------------------------------------------------
RUN pip install --no-cache-dir --break-system-packages \
    pyyaml pillow

# ---------------------------------------------------------------------------
# Working directory and pre-fetched source binaries cache (filled by CI)
# ---------------------------------------------------------------------------
WORKDIR /work

# Helpful defaults
ENV APK_NAME=ShopnoStore \
    EXE_NAME=ShopnoLoginSetup \
    EXE_ARCH=x64

CMD ["/bin/bash"]
