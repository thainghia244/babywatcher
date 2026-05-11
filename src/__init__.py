"""BabyWatcher - Baby Safety Detection System"""

from .detector import BabyWatcher
from .config import Config
from .logger import EventLogger

__version__ = "1.0.0"
__all__ = ["BabyWatcher", "Config", "EventLogger"]
