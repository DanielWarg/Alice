"""
Centralized logging configuration for Alice Ambient Memory system
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_ambient_logging(log_level="INFO", log_file=None):
    """Setup comprehensive logging for the ambient memory system"""
    
    # Create logs directory
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Default log file with timestamp
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"ambient_memory_{timestamp}.log"
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler for detailed logs
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Detailed formatter for file
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Simple formatter for console
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Set specific loggers
    loggers = {
        'ambient_memory': logging.DEBUG,
        'realtime_asr': logging.DEBUG,
        'reflection': logging.DEBUG,
        'orchestrator': logging.INFO,
        'importance': logging.DEBUG,
        'database': logging.INFO,
    }
    
    for logger_name, level in loggers.items():
        specific_logger = logging.getLogger(logger_name)
        specific_logger.setLevel(level)
    
    # Suppress noisy third-party loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    logging.info(f"🚀 Alice Ambient Memory logging initialized")
    logging.info(f"📁 Log file: {log_file}")
    logging.info(f"📊 Log level: {log_level}")
    
    return log_file

class AmbientLogger:
    """Convenience logger wrapper for ambient memory components"""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.component = name
    
    def info(self, msg, **kwargs):
        """Log info with component context"""
        self.logger.info(f"[{self.component}] {msg}", extra=kwargs)
    
    def debug(self, msg, **kwargs):
        """Log debug with component context"""
        self.logger.debug(f"[{self.component}] {msg}", extra=kwargs)
    
    def warning(self, msg, **kwargs):
        """Log warning with component context"""
        self.logger.warning(f"[{self.component}] {msg}", extra=kwargs)
    
    def error(self, msg, **kwargs):
        """Log error with component context"""
        self.logger.error(f"[{self.component}] {msg}", extra=kwargs)
    
    def critical(self, msg, **kwargs):
        """Log critical with component context"""
        self.logger.critical(f"[{self.component}] {msg}", extra=kwargs)
    
    def log_performance(self, operation, duration_ms, **metadata):
        """Log performance metrics"""
        self.logger.info(
            f"[{self.component}] ⚡ {operation} completed in {duration_ms:.2f}ms",
            extra={'operation': operation, 'duration_ms': duration_ms, **metadata}
        )
    
    def log_data_flow(self, stage, count, **metadata):
        """Log data processing stages"""
        self.logger.info(
            f"[{self.component}] 📊 {stage}: {count} items",
            extra={'stage': stage, 'count': count, **metadata}
        )
    
    def log_user_interaction(self, action, **metadata):
        """Log user interactions"""
        self.logger.info(
            f"[{self.component}] 👤 User action: {action}",
            extra={'action': action, **metadata}
        )
    
    def log_system_event(self, event, **metadata):
        """Log system events"""
        self.logger.info(
            f"[{self.component}] 🔧 System event: {event}",
            extra={'event': event, **metadata}
        )
    
    def log_error_with_context(self, error, operation, **context):
        """Log errors with full context"""
        self.logger.error(
            f"[{self.component}] ❌ {operation} failed: {str(error)}",
            extra={'error': str(error), 'operation': operation, **context},
            exc_info=True
        )

def get_logger(component_name: str) -> AmbientLogger:
    """Get a configured logger for a component"""
    return AmbientLogger(component_name)