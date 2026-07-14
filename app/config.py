import os
from typing import Dict, Any, Optional
from loguru import logger


class RegionalConfig:
    """Regional configuration templates for different address systems."""
    
    # Base configurations for different regions
    REGIONAL_TEMPLATES = {
        'US': {
            'name': 'United States',
            'address_parser': {
                'use_libpostal': True,
                'postal_code_pattern': r'^\d{5}(-\d{4})?$',
                'state_abbreviations': True,
                'house_number_priority': 'high',
            },
            'fuzzy_matching': {
                'region_weights': {
                    'house_number': 0.20,
                    'street': 0.25,
                    'city': 0.20,
                    'postal_code': 0.20,
                    'state': 0.10,
                    'country': 0.05,
                },
                'transliteration_support': False,
                'case_sensitive': False,
            },
            'rule_based_filter': {
                'postal_code_threshold': 0.9,
                'street_threshold': 0.7,
                'city_threshold': 0.8,
                'house_number_threshold': 0.8,
                'overall_threshold': 0.7,
                'require_postal_code_match': False,
                'require_city_match': True,
                'require_street_match': True,
                'allow_partial_house_number': True,
                'state_abbreviation_matching': True,
            },
            'geocoding': {
                'country_bias': 'US',
                'max_distance_threshold': 100.0,  # meters
                'use_structured_geocoding': True,
            },
            'ml_model': {
                'use_regional_features': True,
                'confidence_threshold': 0.7,
                'feature_weights': {
                    'postal_code_weight': 0.3,
                    'street_weight': 0.25,
                    'city_weight': 0.2,
                }
            }
        },
        
        'CA': {
            'name': 'Canada',
            'address_parser': {
                'use_libpostal': True,
                'postal_code_pattern': r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$',
                'state_abbreviations': True,
                'house_number_priority': 'high',
            },
            'fuzzy_matching': {
                'region_weights': {
                    'house_number': 0.20,
                    'street': 0.25,
                    'city': 0.20,
                    'postal_code': 0.20,
                    'state': 0.10,
                    'country': 0.05,
                },
                'transliteration_support': False,
                'case_sensitive': False,
            },
            'rule_based_filter': {
                'postal_code_threshold': 0.9,
                'street_threshold': 0.7,
                'city_threshold': 0.8,
                'house_number_threshold': 0.8,
                'overall_threshold': 0.7,
                'require_postal_code_match': False,
                'require_city_match': True,
                'require_street_match': True,
                'allow_partial_house_number': True,
                'state_abbreviation_matching': True,
            },
            'geocoding': {
                'country_bias': 'CA',
                'max_distance_threshold': 100.0,
                'use_structured_geocoding': True,
            },
            'ml_model': {
                'use_regional_features': True,
                'confidence_threshold': 0.7,
                'feature_weights': {
                    'postal_code_weight': 0.3,
                    'street_weight': 0.25,
                    'city_weight': 0.2,
                }
            }
        },
        
        'UK': {
            'name': 'United Kingdom',
            'address_parser': {
                'use_libpostal': True,
                'postal_code_pattern': r'^[A-Z]{1,2}[0-9R][0-9A-Z]?\s?[0-9][A-Z]{2}$',
                'state_abbreviations': False,
                'house_number_priority': 'medium',  # House names common
                'allow_house_names': True,
            },
            'fuzzy_matching': {
                'region_weights': {
                    'house_number': 0.15,  # Less important due to house names
                    'street': 0.25,
                    'city': 0.25,
                    'postal_code': 0.25,  # Very reliable in UK
                    'state': 0.05,
                    'country': 0.05,
                },
                'transliteration_support': False,
                'case_sensitive': False,
            },
            'rule_based_filter': {
                'postal_code_threshold': 0.8,  # More flexible for UK postcodes
                'street_threshold': 0.75,
                'city_threshold': 0.8,
                'house_number_threshold': 0.7,  # More flexible for house names
                'overall_threshold': 0.7,
                'require_postal_code_match': False,
                'require_city_match': True,
                'require_street_match': True,
                'allow_partial_house_number': True,
                'allow_house_names': True,
            },
            'geocoding': {
                'country_bias': 'GB',
                'max_distance_threshold': 50.0,
                'use_structured_geocoding': True,
            },
            'ml_model': {
                'use_regional_features': True,
                'confidence_threshold': 0.7,
                'feature_weights': {
                    'postcode_reliability': 0.35,
                    'house_name_flexibility': 0.15,
                    'street_weight': 0.25,
                }
            }
        },
        
        'DE': {
            'name': 'Germany',
            'address_parser': {
                'use_libpostal': True,
                'postal_code_pattern': r'^\d{5}$',
                'state_abbreviations': False,
                'house_number_priority': 'high',  # Very important in German addresses
                'street_number_after_name': True,
            },
            'fuzzy_matching': {
                'region_weights': {
                    'house_number': 0.25,  # Very important
                    'street': 0.25,
                    'city': 0.20,
                    'postal_code': 0.25,  # PLZ very important
                    'state': 0.05,
                    'country': 0.00,
                },
                'transliteration_support': False,
                'case_sensitive': False,
            },
            'rule_based_filter': {
                'postal_code_threshold': 0.9,
                'street_threshold': 0.8,
                'city_threshold': 0.8,
                'house_number_threshold': 0.9,  # German addresses very precise
                'overall_threshold': 0.75,
                'require_postal_code_match': True,  # PLZ important
                'require_city_match': True,
                'require_street_match': True,
                'allow_partial_house_number': False,  # Strict in Germany
            },
            'geocoding': {
                'country_bias': 'DE',
                'max_distance_threshold': 50.0,
                'use_structured_geocoding': True,
            },
            'ml_model': {
                'use_regional_features': True,
                'confidence_threshold': 0.75,
                'feature_weights': {
                    'house_number_precision': 0.3,
                    'postal_city_combo': 0.3,
                    'street_weight': 0.25,
                }
            }
        },
        
        'FR': {
            'name': 'France',
            'address_parser': {
                'use_libpostal': True,
                'postal_code_pattern': r'^\d{5}$',
                'state_abbreviations': False,
                'house_number_priority': 'high',
                'number_before_street': True,
            },
            'fuzzy_matching': {
                'region_weights': {
                    'house_number': 0.20,
                    'street': 0.25,
                    'city': 0.25,
                    'postal_code': 0.25,
                    'state': 0.05,
                    'country': 0.00,
                },
                'transliteration_support': False,
                'case_sensitive': False,
            },
            'rule_based_filter': {
                'postal_code_threshold': 0.9,
                'street_threshold': 0.75,
                'city_threshold': 0.8,
                'house_number_threshold': 0.8,
                'overall_threshold': 0.7,
                'require_postal_code_match': False,
                'require_city_match': True,
                'require_street_match': True,
                'allow_partial_house_number': True,
            },
            'geocoding': {
                'country_bias': 'FR',
                'max_distance_threshold': 75.0,
                'use_structured_geocoding': True,
            },
            'ml_model': {
                'use_regional_features': True,
                'confidence_threshold': 0.7,
                'feature_weights': {
                    'postal_code_weight': 0.3,
                    'street_weight': 0.25,
                    'city_weight': 0.25,
                }
            }
        },
        
        'IN': {
            'name': 'India',
            'address_parser': {
                'use_libpostal': True,
                'postal_code_pattern': r'^\d{6}$',
                'state_abbreviations': False,
                'house_number_priority': 'medium',  # Complex numbering systems
                'support_flat_numbers': True,
                'support_locality_areas': True,
            },
            'fuzzy_matching': {
                'region_weights': {
                    'house_number': 0.10,  # Less reliable
                    'street': 0.15,  # Often inconsistent
                    'city': 0.25,
                    'postal_code': 0.35,  # Pincode very important
                    'state': 0.10,
                    'country': 0.05,
                },
                'transliteration_support': True,  # Important for Indian addresses
                'case_sensitive': False,
                'locality_matching': True,
            },
            'rule_based_filter': {
                'postal_code_threshold': 0.9,  # Pincode very important
                'street_threshold': 0.6,  # More flexible for complex Indian addresses
                'city_threshold': 0.7,  # More flexible for city name variations
                'house_number_threshold': 0.6,  # Indian house numbers can be complex
                'overall_threshold': 0.65,  # Lower overall threshold
                'require_postal_code_match': True,  # Pincode critical
                'require_city_match': True,
                'require_street_match': False,  # Street info often inconsistent
                'allow_partial_house_number': True,
                'allow_area_locality_matching': True,  # Indian addresses have areas/localities
            },
            'geocoding': {
                'country_bias': 'IN',
                'max_distance_threshold': 200.0,  # Higher due to density
                'use_structured_geocoding': True,
                'fallback_to_pincode': True,
            },
            'ml_model': {
                'use_regional_features': True,
                'confidence_threshold': 0.65,  # Lower threshold for Indian addresses
                'feature_weights': {
                    'pincode_weight': 0.4,
                    'city_flexibility': 0.25,
                    'street_weight': 0.15,
                    'locality_weight': 0.2,
                }
            }
        },
        
        'AU': {
            'name': 'Australia',
            'address_parser': {
                'use_libpostal': True,
                'postal_code_pattern': r'^\d{4}$',
                'state_abbreviations': True,
                'house_number_priority': 'high',
            },
            'fuzzy_matching': {
                'region_weights': {
                    'house_number': 0.20,
                    'street': 0.25,
                    'city': 0.20,
                    'postal_code': 0.20,
                    'state': 0.10,
                    'country': 0.05,
                },
                'transliteration_support': False,
                'case_sensitive': False,
            },
            'rule_based_filter': {
                'postal_code_threshold': 0.9,
                'street_threshold': 0.75,
                'city_threshold': 0.8,
                'house_number_threshold': 0.8,
                'overall_threshold': 0.7,
                'require_postal_code_match': False,
                'require_city_match': True,
                'require_street_match': True,
                'allow_partial_house_number': True,
                'state_abbreviation_matching': True,
            },
            'geocoding': {
                'country_bias': 'AU',
                'max_distance_threshold': 100.0,
                'use_structured_geocoding': True,
            },
            'ml_model': {
                'use_regional_features': True,
                'confidence_threshold': 0.7,
                'feature_weights': {
                    'postal_code_weight': 0.3,
                    'street_weight': 0.25,
                    'city_weight': 0.2,
                }
            }
        },
    }
    
    @classmethod
    def get_region_config(cls, region: str) -> Dict[str, Any]:
        """Get configuration for a specific region."""
        return cls.REGIONAL_TEMPLATES.get(region, cls.REGIONAL_TEMPLATES['US'])
    
    @classmethod
    def get_supported_regions(cls) -> list[str]:
        """Get list of all supported regions."""
        return list(cls.REGIONAL_TEMPLATES.keys())


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
            env_config['rule_based_filter'] = rules_config
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
        rules = self.get_component_config('rule_based_filter')
        ml = self.get_component_config('ml_model')

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
            'ml_model_path': ml.get('model_path'),
            'ml_auto_train': ml.get('auto_train', False),
            'rules': rules,
            'log_level': system.get('log_level', 'INFO'),
            'api_host': system.get('api_host', '0.0.0.0'),
            'api_port': system.get('api_port', 8000),
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