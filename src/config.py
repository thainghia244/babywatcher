"""Configuration management for BabyWatcher"""

import yaml
import os
from typing import Dict, Any
from pathlib import Path


class Config:
    """Load and manage configuration from YAML file"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config.yaml file
        """
        self.config_path = config_path
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            print(f"✅ Configuration loaded from {self.config_path}")
        except Exception as e:
            raise RuntimeError(f"Error loading config file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., "detection.img_size")
            default: Default value if key not found
        
        Returns:
            Configuration value
        
        Example:
            >>> config.get("detection.img_size")
            640
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def get_dict(self, section: str) -> Dict[str, Any]:
        """
        Get entire section as dictionary
        
        Args:
            section: Section name (e.g., "detection", "alerts")
        
        Returns:
            Section configuration dictionary
        """
        return self.config.get(section, {})
    
    def __repr__(self) -> str:
        return f"<Config from {self.config_path}>"


# Global config instance
_config_instance = None


def get_config(config_path: str = "config.yaml") -> Config:
    """
    Get or create global config instance (singleton pattern)
    
    Args:
        config_path: Path to config.yaml file
    
    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
