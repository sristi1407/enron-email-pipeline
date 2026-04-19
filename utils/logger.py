#!/usr/bin/env python3
"""Centralized logging configuration"""

import logging
import sys
from pathlib import Path

def setup_logger(name: str, log_file: str = "pipeline.log"):
    """Setup logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # File handler - writes to file
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)
    
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    
    # Console handler - prints to screen
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    
    # Formatter - how messages look
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger