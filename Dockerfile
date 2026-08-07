# ==============================================================================
#  CodeRunner.AI  ::  Container Image
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Base    : python:3.11-slim
#  Purpose : Ephemeral container for the terminal Code Interpreter chatbot.
# ==============================================================================

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TERM=xterm-256color \
    # milvus-lite talks gRPC over loopback, and the gRPC C-core logs
    # "Got goaway ... too_many_pings" straight to stderr from C++. That is
    # BENEATH Python's logging module, so vectorstore.py's
    # logging.getLogger("pymilvus").setLevel(CRITICAL) cannot reach it — two
    # lines per session were landing inside Rich-rendered panels. Measured:
    # 2 lines -> 0 with these set. SPEC-MEMORY-001 v1.1.0.
    GRPC_VERBOSITY=NONE \
    GLOG_minloglevel=3

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY main.py tools.py memory.py recall.py vectorstore.py params.py settings.py ./

# The `.coderunner` directory MUST exist in the image AND be owned by `runner`
# BEFORE `USER runner`. Docker copies an image directory's ownership into an
# empty named volume at mount time; a mount path that is absent from the image
# yields a ROOT-owned volume and `runner` can never write memory.db. The memory
# subsystem would then take its graceful-degradation path on every turn and hide
# the fault. See SPEC-MEMORY-001 §3.1 (trap A) and the V1 verification.
RUN useradd --create-home --shell /bin/bash runner \
 && mkdir -p /home/runner/.coderunner \
 && chown -R runner:runner /home/runner/.coderunner \
 && chown -R runner:runner /app
USER runner

ENTRYPOINT ["python", "-u", "main.py"]
