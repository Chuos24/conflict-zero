"""
app/core/logging_setup.py
Structured Logging with structlog + Sentry
"""

import structlog
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
import os
import sys

def setup_structlog():
    """Configure structlog for structured JSON logging"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()  # JSON output
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
        handlers=[logging.StreamHandler()],
    )

def setup_sentry():
    """Initialize Sentry for centralized error tracking"""
    sentry_dsn = os.environ.get('SENTRY_DSN')
    
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,  # 10% of transactions
            environment=os.environ.get('ENVIRONMENT', 'production'),
            debug=os.environ.get('DEBUG', 'false').lower() == 'true'
        )
        logger = structlog.get_logger()
        logger.info("sentry_initialized", dsn_set=True)
    else:
        logger = structlog.get_logger()
        logger.warning("sentry_not_configured", dsn_provided=False)

def get_logger(name: str = __name__):
    """Get a structlog logger instance"""
    return structlog.get_logger(name)

