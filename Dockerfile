# ==============================================================================
#  CodeRunner.AI  ::  Container Image
# ------------------------------------------------------------------------------
#  Author  : kurapa <kurapa@kurapa.com>
#  Base    : python:3.11-slim
#  Purpose : Ephemeral container for the terminal Code Interpreter chatbot.
# ==============================================================================

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TERM=xterm-256color

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY main.py tools.py ./

RUN useradd --create-home --shell /bin/bash runner \
 && chown -R runner:runner /app
USER runner

ENTRYPOINT ["python", "-u", "main.py"]
