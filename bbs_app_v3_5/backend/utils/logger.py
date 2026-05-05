"""Application-wide logger setup.

On Vercel (or any serverless / read-only filesystem environment) the file
handler is silently skipped — we only stream to stdout. Vercel's dashboard
captures stdout as the function's logs automatically.
"""
import logging
import os
from logging.handlers import RotatingFileHandler


def _is_serverless() -> bool:
    """Detect Vercel / AWS Lambda / similar read-only-fs environments."""
    return any(os.environ.get(k) for k in
               ("VERCEL", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME"))


def setup_logger(name: str = "bbs_app", log_dir: str = "logs") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:    # already configured
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — only on filesystems that allow writes (i.e. NOT serverless).
    if not _is_serverless():
        try:
            os.makedirs(log_dir, exist_ok=True)
            fh = RotatingFileHandler(
                os.path.join(log_dir, "app.log"),
                maxBytes=2_000_000, backupCount=5
            )
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        except OSError:
            # Read-only fs surfaced unexpectedly — just skip the file handler.
            pass

    # Stream handler always works (Vercel captures it as function logs)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger
