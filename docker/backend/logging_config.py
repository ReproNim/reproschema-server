"""
Logging configuration for ReproSchema Server
Provides structured logging with proper security considerations
"""
import os
import sys
import logging
import logging.config
from datetime import datetime
from typing import Dict, Any

class SecurityFilter(logging.Filter):
    """Filter to prevent logging of sensitive information"""
    
    SENSITIVE_KEYWORDS = [
        'password', 'token', 'key', 'secret', 'auth', 'credential',
        'bearer', 'jwt', 'session', 'cookie'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out sensitive information from logs"""
        message = record.getMessage().lower()
        
        # Check if message contains sensitive keywords
        for keyword in self.SENSITIVE_KEYWORDS:
            if keyword in message:
                # Replace the entire message with a generic one
                record.msg = "[REDACTED - Sensitive information filtered]"
                record.args = ()
                break
        
        return True

class ReproSchemaFormatter(logging.Formatter):
    """Custom formatter for ReproSchema logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with additional context"""
        # Add timestamp in ISO format
        record.timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Add service name
        record.service = 'reproschema-server'
        
        # Add request ID if available (from request context)
        record.request_id = getattr(record, 'request_id', 'unknown')
        
        return super().format(record)

def setup_logging(log_level: str = None, log_file: str = None) -> None:
    """Configure logging for the application"""
    
    # Determine log level
    if not log_level:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Validate log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}, using INFO")
        numeric_level = logging.INFO
    
    # Create logs directory if using file logging
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                '()': ReproSchemaFormatter,
                'format': '[{timestamp}] {service} {levelname} [{request_id}] {name}: {message}',
                'style': '{'
            },
            'simple': {
                'format': '[{asctime}] {levelname} {name}: {message}',
                'style': '{'
            }
        },
        'filters': {
            'security': {
                '()': SecurityFilter
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'simple',
                'filters': ['security'],
                'stream': sys.stdout
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console']
        },
        'loggers': {
            'reproschema': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'sanic': {
                'level': 'WARNING',  # Reduce Sanic noise
                'handlers': ['console'],
                'propagate': False
            },
            'urllib3': {
                'level': 'WARNING',  # Reduce requests noise
                'handlers': ['console'],
                'propagate': False
            }
        }
    }
    
    # Add file handler if specified
    if log_file:
        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'detailed',
            'filters': ['security'],
            'filename': log_file,
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'encoding': 'utf-8'
        }
        
        # Add file handler to all loggers
        config['root']['handlers'].append('file')
        for logger_config in config['loggers'].values():
            logger_config['handlers'].append('file')
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Log startup message
    logger = logging.getLogger('reproschema.startup')
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file or 'None'}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the reproschema prefix"""
    return logging.getLogger(f"reproschema.{name}")

def add_request_id(record: logging.LogRecord, request_id: str) -> None:
    """Add request ID to log record"""
    record.request_id = request_id

# Context manager for request logging
class RequestLogger:
    """Context manager to add request context to logs"""
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.request_id = self.request_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)