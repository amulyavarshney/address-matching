import os
from typing import Dict, Any, Optional
from loguru import logger


class RegionalConfig:
    """Regional configuration templates backed by RegionRegistry."""

    @classmethod
    def get_region_config(cls, region: str) -> Dict[str, Any]:
        """Get configuration for a specific region."""
        from app.regions import RegionRegistry
        return RegionRegistry.get_template(region)

    @classmethod
    def get_supported_regions(cls) -> list[str]:
        """Get list of all supported regions."""
        from app.regions import RegionRegistry
        return RegionRegistry.supported_regions()


class AddressMatchingConfig:
    """
    Enhanced configuration management for the address matching system with regional support.
    """
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        region: str = 'US',
        apply_env: bool = True,
    ):
        """
        Initialize configuration.
        
        Args:
            config_file: Optional path to configuration file
            region: Default region for address matching
            apply_env: Whether to merge environment variable overrides
        """
        self.region = region
        self.regional_config = RegionalConfig()
        
        # Load base configuration
        self._base_config = self._load_base_config()
        
        # Load region-specific configuration
        self._region_config = self.regional_config.get_region_config(region)
        
        # Load user configuration from file if provided
        self._user_config = {}
        if config_file and os.path.exists(config_file):
            self._user_config = self._load_config_file(config_file)
        
        # Merge configurations (user config takes precedence)
        self.config = self._merge_configs()

        # Environment overrides win over file/base config
        if apply_env:
            env_overrides = self.get_environment_specific_config()
            if env_overrides:
                self.config = self._deep_merge(self.config, env_overrides)
                env_region = (
                    env_overrides.get('system', {}).get('default_region')
                )
                if env_region and env_region != self.region:
                    self.region = env_region
        
        logger.info(f"Configuration initialized for region {self.region}")
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load base system configuration."""
        return {
            'system': {
                'default_region': 'US',
                'auto_detect_region': True,
                'max_concurrent_requests': 10,
                'request_timeout': 30.0,
                'enable_caching': True,
                'cache_ttl': 3600,  # 1 hour
                'log_level': 'INFO',
            },
            'components': {
                'use_libpostal': True,
                'use_ml_model': True,
                'use_geospatial': True,
                'use_caching': True,
            },
            'performance': {
                'batch_size': 100,
                'enable_parallel_processing': True,
                'max_workers': 4,
            },
            'security': {
                'rate_limiting': True,
                'max_requests_per_minute': 60,
                'api_key_required': False,
                'cors_origins': ['*'],
                'max_address_length': 500,
                'max_batch_size': 50,
            },
            'logging': {
                'log_requests': True,
                'log_responses': False,
                'log_performance': True,
                'retention_days': 30,
            }
        }
    
    def _load_config_file(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            import json
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file {config_file}: {e}")
            return {}
    
    def _merge_configs(self) -> Dict[str, Any]:
        """Merge base, regional, and user configurations."""
        config = {}
        
        # Start with base config
        config.update(self._base_config)
        
        # Add regional configurations
        for component in ['address_parser', 'fuzzy_matching', 'rule_based_filter', 'geocoding', 'ml_model']:
            if component in self._region_config:
                if component not in config:
                    config[component] = {}
                config[component].update(self._region_config[component])
        
        # Apply user overrides
        config = self._deep_merge(config, self._user_config)
        
        return config
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_component_config(self, component: str) -> Dict[str, Any]:
        """
        Get configuration for a specific component.
        
        Args:
            component: Component name (address_parser, fuzzy_matching, etc.)
            
        Returns:
            Component configuration dictionary
        """
        return self.config.get(component, {})
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get system-level configuration."""
        return self.config.get('system', {})
    
    def set_region(self, region: str):
        """
        Change the active region and reload configuration.
        
        Args:
            region: New region code
        """
        if region not in self.regional_config.get_supported_regions():
            logger.warning(f"Region {region} not supported, using default US")
            region = 'US'
        
        self.region = region
        self._region_config = self.regional_config.get_region_config(region)
        self.config = self._merge_configs()
        
        logger.info(f"Switched to region {region}")
    
    def update_config(self, updates: Dict[str, Any]):
        """
        Update configuration with new values.
        
        Args:
            updates: Dictionary of configuration updates
        """
        self.config = self._deep_merge(self.config, updates)
        logger.info(f"Configuration updated: {list(updates.keys())}")
    
    def get_region_specific_threshold(self, component: str, threshold_name: str) -> float:
        """
        Get a region-specific threshold value.
        
        Args:
            component: Component name
            threshold_name: Threshold parameter name
            
        Returns:
            Threshold value
        """
        component_config = self.get_component_config(component)
        return component_config.get(threshold_name, 0.7)  # Default threshold
    
    def get_supported_regions(self) -> list[str]:
        """Get list of supported regions."""
        return self.regional_config.get_supported_regions()
    
    def export_config(self, file_path: str):
        """
        Export current configuration to file.
        
        Args:
            file_path: Path to save configuration
        """
        try:
            import json
            with open(file_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration exported to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export config to {file_path}: {e}")
    
    def validate_config(self) -> list[str]:
        """
        Validate current configuration and return any issues.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Validate system config
        system_config = self.get_system_config()
        if system_config.get('max_concurrent_requests', 0) <= 0:
            errors.append("max_concurrent_requests must be positive")
        
        if system_config.get('request_timeout', 0) <= 0:
            errors.append("request_timeout must be positive")
        
        # Validate component configurations
        for component in ['address_parser', 'fuzzy_matching', 'rule_based_filter']:
            component_config = self.get_component_config(component)
            
            # Check for required thresholds
            if component == 'rule_based_filter':
                required_thresholds = ['overall_threshold', 'city_threshold', 'street_threshold']
                for threshold in required_thresholds:
                    value = component_config.get(threshold)
                    if value is None or not (0.0 <= value <= 1.0):
                        errors.append(f"{component}.{threshold} must be between 0.0 and 1.0")
        
        # Validate region-specific weights
        fuzzy_config = self.get_component_config('fuzzy_matching')
        weights = fuzzy_config.get('region_weights', {})
        if weights:
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:  # Allow small floating point differences
                errors.append(f"fuzzy_matching.region_weights should sum to 1.0, got {total_weight}")
        
        return errors
    
    @staticmethod
    def _env_bool(name: str) -> Optional[bool]:
        """Parse a boolean environment variable if set."""
        value = os.getenv(name)
        if value is None:
            return None
        return value.strip().lower() in ('1', 'true', 'yes', 'on')

    @staticmethod
    def _env_float(name: str) -> Optional[float]:
        """Parse a float environment variable if set."""
        value = os.getenv(name)
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Invalid float for {name}={value!r}, ignoring")
            return None

    @staticmethod
    def _env_int(name: str) -> Optional[int]:
        """Parse an int environment variable if set."""
        value = os.getenv(name)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Invalid int for {name}={value!r}, ignoring")
            return None

    def get_environment_specific_config(self) -> Dict[str, Any]:
        """Get configuration based on environment variables."""
        env_config: Dict[str, Any] = {}
        system_config: Dict[str, Any] = {}
        components_config: Dict[str, Any] = {}
        geocoding_config: Dict[str, Any] = {}
        rules_config: Dict[str, Any] = {}
        ml_config: Dict[str, Any] = {}
        security_config: Dict[str, Any] = {}

        # System / API
        region = os.getenv('ADDRESS_MATCHING_REGION')
        if region:
            system_config['default_region'] = region.upper()

        log_level = os.getenv('ADDRESS_MATCHING_LOG_LEVEL') or os.getenv('LOG_LEVEL')
        if log_level:
            system_config['log_level'] = log_level.upper()

        api_host = os.getenv('API_HOST')
        if api_host:
            system_config['api_host'] = api_host

        api_port = self._env_int('API_PORT')
        if api_port is not None:
            system_config['api_port'] = api_port

        # Security / API surface
        api_key = os.getenv('API_KEY')
        if api_key is not None:
            security_config['api_key'] = api_key.strip()

        cors_origins = os.getenv('CORS_ORIGINS')
        if cors_origins is not None:
            origins = [o.strip() for o in cors_origins.split(',') if o.strip()]
            security_config['cors_origins'] = origins or ['*']

        max_address_length = self._env_int('MAX_ADDRESS_LENGTH')
        if max_address_length is not None:
            security_config['max_address_length'] = max_address_length

        max_batch_size = self._env_int('MAX_BATCH_SIZE')
        if max_batch_size is not None:
            security_config['max_batch_size'] = max_batch_size

        rate_limiting = self._env_bool('RATE_LIMITING')
        if rate_limiting is not None:
            security_config['rate_limiting'] = rate_limiting

        max_rpm = self._env_int('MAX_REQUESTS_PER_MINUTE')
        if max_rpm is not None:
            security_config['max_requests_per_minute'] = max_rpm

        geo_provider = os.getenv('GEOCODING_PROVIDER')
        if geo_provider:
            geocoding_config['provider'] = geo_provider.strip().lower()

        geo_api_key = (
            os.getenv('GEOCODING_API_KEY')
            or os.getenv('GOOGLE_GEOCODING_API_KEY')
            or os.getenv('MAPBOX_ACCESS_TOKEN')
        )
        if geo_api_key:
            geocoding_config['api_key'] = geo_api_key

        # Component toggles (DISABLE_* wins over USE_*)
        use_ml = self._env_bool('USE_ML_MODEL')
        if use_ml is not None:
            components_config['use_ml_model'] = use_ml
        if os.getenv('DISABLE_ML_MODEL') == '1':
            components_config['use_ml_model'] = False

        use_geo = self._env_bool('USE_GEOSPATIAL')
        if use_geo is not None:
            components_config['use_geospatial'] = use_geo
        if os.getenv('DISABLE_GEOSPATIAL') == '1':
            components_config['use_geospatial'] = False

        if os.getenv('DISABLE_LIBPOSTAL') == '1':
            components_config['use_libpostal'] = False

        # Geocoding
        user_agent = os.getenv('GEOCODING_USER_AGENT')
        if user_agent:
            geocoding_config['user_agent'] = user_agent

        geo_timeout = self._env_int('GEOCODING_TIMEOUT')
        if geo_timeout is not None:
            geocoding_config['timeout'] = geo_timeout

        distance_threshold = self._env_float('DISTANCE_THRESHOLD')
        if distance_threshold is not None:
            geocoding_config['max_distance_threshold'] = distance_threshold

        # Rule-based thresholds
        threshold_env_map = {
            'POSTAL_CODE_THRESHOLD': 'postal_code_threshold',
            'STREET_THRESHOLD': 'street_threshold',
            'CITY_THRESHOLD': 'city_threshold',
            'HOUSE_NUMBER_THRESHOLD': 'house_number_threshold',
            'OVERALL_THRESHOLD': 'overall_threshold',
        }
        for env_name, config_key in threshold_env_map.items():
            value = self._env_float(env_name)
            if value is not None:
                rules_config[config_key] = value

        require_map = {
            'REQUIRE_POSTAL_CODE_MATCH': 'require_postal_code_match',
            'REQUIRE_CITY_MATCH': 'require_city_match',
            'REQUIRE_STREET_MATCH': 'require_street_match',
        }
        for env_name, config_key in require_map.items():
            value = self._env_bool(env_name)
            if value is not None:
                rules_config[config_key] = value

        # ML
        ml_model_path = os.getenv('ML_MODEL_PATH')
        if ml_model_path:
            ml_config['model_path'] = ml_model_path

        ml_auto_train = self._env_bool('ML_AUTO_TRAIN')
        if ml_auto_train is not None:
            ml_config['auto_train'] = ml_auto_train

        if system_config:
            env_config['system'] = system_config
        if components_config:
            env_config['components'] = components_config
        if geocoding_config:
            env_config['geocoding'] = geocoding_config
        if rules_config:
            env_config['rule_overrides'] = rules_config
        if ml_config:
            env_config['ml_model'] = ml_config
        if security_config:
            env_config['security'] = security_config

        return env_config

    def to_matcher_config(self) -> Dict[str, Any]:
        """
        Flatten nested config into the dict expected by AddressMatcher.
        """
        system = self.get_system_config()
        components = self.config.get('components', {})
        geocoding = self.get_component_config('geocoding')
        ml = self.get_component_config('ml_model')
        security = self.config.get('security', {})

        return {
            'default_region': system.get('default_region', self.region),
            'auto_detect_region': system.get('auto_detect_region', True),
            'use_ml_model': components.get('use_ml_model', True),
            'use_geospatial': components.get('use_geospatial', True),
            'distance_threshold': geocoding.get('max_distance_threshold', 50.0),
            'geocoding_user_agent': geocoding.get(
                'user_agent', 'address-matching-service'
            ),
            'geocoding_timeout': geocoding.get('timeout', 10),
            'geocoding_provider': geocoding.get('provider', 'nominatim'),
            'geocoding_api_key': geocoding.get('api_key'),
            'ml_model_path': ml.get('model_path'),
            'ml_auto_train': ml.get('auto_train', False),
            # Global threshold overrides only — never full regional templates
            'rule_overrides': self.config.get('rule_overrides', {}),
            'log_level': system.get('log_level', 'INFO'),
            'api_host': system.get('api_host', '0.0.0.0'),
            'api_port': system.get('api_port', 8000),
            'rate_limiting': security.get('rate_limiting', True),
            'max_requests_per_minute': security.get('max_requests_per_minute', 60),
        }

    def to_api_settings(self) -> Dict[str, Any]:
        """Settings for HTTP layer (auth, CORS, limits)."""
        security = self.config.get('security', {})
        cors_origins = security.get('cors_origins', ['*'])
        if isinstance(cors_origins, str):
            cors_origins = [o.strip() for o in cors_origins.split(',') if o.strip()] or ['*']

        api_key = security.get('api_key') or os.getenv('API_KEY')
        if api_key is not None:
            api_key = str(api_key).strip() or None

        return {
            'api_key': api_key,
            'cors_origins': cors_origins,
            'max_address_length': int(security.get('max_address_length', 500)),
            'max_batch_size': int(security.get('max_batch_size', 50)),
            'rate_limiting': bool(security.get('rate_limiting', True)),
            'max_requests_per_minute': int(security.get('max_requests_per_minute', 60)),
        }
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"AddressMatchingConfig(region={self.region}, components={list(self.config.keys())})"
    
    def __repr__(self) -> str:
        """Detailed representation of configuration."""
        return f"AddressMatchingConfig(region={self.region}, config_keys={list(self.config.keys())})"


# Global configuration instance
_global_config = None

def get_config(region: str = 'US', config_file: Optional[str] = None) -> AddressMatchingConfig:
    """
    Get global configuration instance.
    
    Args:
        region: Default region
        config_file: Optional configuration file
        
    Returns:
        AddressMatchingConfig instance
    """
    global _global_config
    
    if _global_config is None:
        _global_config = AddressMatchingConfig(config_file, region)
    
    return _global_config

def set_global_config(config: AddressMatchingConfig):
    """Set the global configuration instance."""
    global _global_config
    _global_config = config

def load_config_from_file(file_path: str, region: str = 'US') -> AddressMatchingConfig:
    """
    Load configuration from file.
    
    Args:
        file_path: Path to configuration file
        region: Default region
        
    Returns:
        AddressMatchingConfig instance
    """
    return AddressMatchingConfig(file_path, region) 