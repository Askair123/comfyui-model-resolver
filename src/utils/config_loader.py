"""
Configuration Loader Module

Loads and manages configuration from YAML files with environment variable support.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import re


class ConfigLoader:
    """Loads and manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_path: Path to main configuration file
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Navigate from src/utils to config directory
        current_dir = Path(__file__).parent
        config_path = current_dir.parent.parent / "config" / "default_config.yaml"
        return str(config_path)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Process environment variables
        config = self._process_env_vars(config)
        
        # Load additional config files if specified
        if 'include' in config:
            for include_file in config['include']:
                include_path = Path(self.config_path).parent / include_file
                if include_path.exists():
                    with open(include_path, 'r') as f:
                        include_config = yaml.safe_load(f)
                        config = self._merge_configs(config, include_config)
        
        return config
    
    def _process_env_vars(self, config: Any) -> Any:
        """
        Recursively process environment variables in configuration.
        
        Replaces ${VAR_NAME} with environment variable values.
        """
        if isinstance(config, dict):
            return {k: self._process_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._process_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Look for ${VAR_NAME} pattern
            pattern = r'\$\{([^}]+)\}'
            
            def replacer(match):
                var_name = match.group(1)
                # Support default values: ${VAR_NAME:default_value}
                if ':' in var_name:
                    var_name, default = var_name.split(':', 1)
                    return os.getenv(var_name, default)
                return os.getenv(var_name, match.group(0))
            
            return re.sub(pattern, replacer, config)
        else:
            return config
    
    def _merge_configs(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two configuration dictionaries.
        
        Args:
            base: Base configuration
            overlay: Configuration to overlay on top
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_path(self, key_path: str, default: Optional[str] = None) -> Optional[Path]:
        """
        Get a configuration path value and expand it.
        
        Args:
            key_path: Dot-separated path to configuration key
            default: Default path if key not found
            
        Returns:
            Expanded Path object or None
        """
        path_str = self.get(key_path, default)
        if path_str is None:
            return None
        
        # Expand user home directory
        path_str = os.path.expanduser(path_str)
        
        # Make relative paths absolute based on config file location
        path = Path(path_str)
        if not path.is_absolute():
            config_dir = Path(self.config_path).parent
            path = config_dir / path
        
        return path
    
    def reload(self):
        """Reload configuration from file."""
        self.config = self._load_config()
    
    def save_user_config(self, user_config: Dict[str, Any], 
                        output_path: Optional[str] = None):
        """
        Save user configuration to a file.
        
        Args:
            user_config: User configuration to save
            output_path: Output file path (defaults to config/local_config.yaml)
        """
        if output_path is None:
            config_dir = Path(self.config_path).parent
            output_path = config_dir / "local_config.yaml"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(user_config, f, default_flow_style=False, sort_keys=False)
    
    def validate(self, required_keys: list) -> bool:
        """
        Validate that required configuration keys exist.
        
        Args:
            required_keys: List of required key paths
            
        Returns:
            True if all required keys exist
        """
        for key_path in required_keys:
            if self.get(key_path) is None:
                return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Get the full configuration as a dictionary."""
        return self.config.copy()