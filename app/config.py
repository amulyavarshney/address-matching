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
    
    def __init__(self, config_file: Optional[str] = None, region: str = 'US'):
        """
        Initialize configuration.
        
        Args:
            config_file: Optional path to configuration file
            region: Default region for address matching
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
        
        logger.info(f"Configuration initialized for region {region}")
    
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
    
    def get_environment_specific_config(self) -> Dict[str, Any]:
        """Get configuration based on environment variables."""
        env_config = {}
        
        # System environment variables
        if os.getenv('ADDRESS_MATCHING_REGION'):
            env_config['system'] = {'default_region': os.getenv('ADDRESS_MATCHING_REGION')}
        
        if os.getenv('ADDRESS_MATCHING_LOG_LEVEL'):
            if 'system' not in env_config:
                env_config['system'] = {}
            env_config['system']['log_level'] = os.getenv('ADDRESS_MATCHING_LOG_LEVEL')
        
        # Component toggles
        components_config = {}
        if os.getenv('DISABLE_LIBPOSTAL') == '1':
            components_config['use_libpostal'] = False
        
        if os.getenv('DISABLE_ML_MODEL') == '1':
            components_config['use_ml_model'] = False
        
        if os.getenv('DISABLE_GEOSPATIAL') == '1':
            components_config['use_geospatial'] = False
        
        if components_config:
            env_config['components'] = components_config
        
        return env_config
    
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