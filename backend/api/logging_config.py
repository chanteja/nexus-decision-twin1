# backend/api/logging_config.py
"""Structured JSON logging — one event per line, machine-parseable, CloudWatch-ready.

Every record carries timestamp, level, logger, message, and any structured fields
passed via ``extra=`` (e.g. request_id, tenant, path). No PII is logged by default.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k not in _RESERVED and not k.startswith("_"):
                payload[k] = v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging() -> logging.Logger:
    level = os.environ.get("NEXUS_LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)
    # idempotent: replace handlers so re-import in tests doesn't duplicate lines
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    return logging.getLogger("nexus")
