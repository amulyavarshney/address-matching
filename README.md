# Address Matching Microservice

A comprehensive RESTful microservice for address matching that incorporates address normalization, fuzzy string matching, rule-based filtering, machine learning-based entity resolution, and geospatial validation.

## Features

- **Address Normalization & Parsing**: Uses libpostal (or fallback regex) to extract and normalize address components
- **Fuzzy String Matching**: Computes similarity scores using RapidFuzz with component-specific algorithms
- **Rule-Based Filtering**: Configurable rules for postal codes, street names, and other components
- **Machine Learning**: Optional ML model for entity resolution with synthetic training data
- **Geospatial Validation**: Uses OpenStreetMap Nominatim for geocoding and distance calculation
- **Comprehensive API**: RESTful endpoint with detailed response including confidence scores
- **Error Handling**: Graceful degradation when optional services are unavailable
- **Performance**: Caching and rate limiting for external API calls

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd address-matching
```

2. Install core dependencies:
```bash
pip install -r requirements.txt
```

For development/tests:
```bash
pip install -r requirements-dev.txt
```

3. (Optional but Recommended) Install libpostal for enhanced address parsing:

**On Ubuntu/Debian:**
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y curl autoconf automake libtool pkg-config

# Download and build libpostal
git clone https://github.com/openvenues/libpostal
cd libpostal
./bootstrap.sh
./configure --datadir=/usr/local/share/libpostal
make -j4
sudo make install

# Update library cache
sudo ldconfig

# Install Python bindings
cd ..
pip install -r requirements-optional.txt
```

**On macOS:**
```bash
# Install libpostal via Homebrew
brew install libpostal

# Install Python bindings  
pip install -r requirements-optional.txt
```

**Note:** The service works without libpostal using a fallback regex-based parser, but libpostal provides significantly better address parsing accuracy.

### Running the Service

#### Option 1: Direct Python Execution

**Recommended - with dependency checking:**
```bash
python run.py
```

**Alternative methods:**
```bash
# Direct execution
python main.py

# Using uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Option 2: Docker
```bash
# Build and run with Docker Compose
docker compose up --build

# Or build/run manually
docker build -t address-matching .
docker run -p 8000:8000 address-matching
```

The API will be available at `http://localhost:8000`.
View the interactive API documentation at `/docs`.

## API Usage

### Match Addresses Endpoint

**POST** `/match-addresses`

#### Request Body

```json
{
  "address1": "string",
  "address2": "string"
}
```

#### Response

```json
{
  "match": true,
  "confidence_score": 0.92,
  "details": {
    "normalized_address1": {
      "house_number": "221B",
      "street": "Baker Street",
      "city": "London",
      "postal_code": "NW1 6XE",
      "country": "UK"
    },
    "normalized_address2": {
      "house_number": "221-B",
      "street": "Baker Street",
      "city": "London",
      "postal_code": "NW1 6XE",
      "country": "United Kingdom"
    },
    "component_similarities": {
      "house_number": 0.9,
      "street": 1.0,
      "city": 1.0,
      "postal_code": 1.0,
      "country": 0.8
    },
    "geospatial_distance_meters": 12.5,
    "rule_based_decision": true,
    "ml_model_decision": true
  }
}
```

### Example Requests

#### Using curl

```bash
curl -X POST "http://localhost:8000/match-addresses" \
     -H "Content-Type: application/json" \
     -d '{
       "address1": "221B Baker St., London NW1 6XE, UK",
       "address2": "221-B Baker Street, NW1 6XE London, United Kingdom"
     }'
```

#### Using Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/match-addresses",
    json={
        "address1": "123 Main Street, New York, NY 10001",
        "address2": "123 Main St, NYC, NY 10001"
    }
)

result = response.json()
print(f"Match: {result['match']}")
print(f"Confidence: {result['confidence_score']}")
```

### Health Check

**GET** `/health`

Liveness probe — returns `{"status": "healthy"}` when the process is up.

**GET** `/health/ready`

Readiness probe — reports component status. Returns HTTP 503 when enabled features
(ML / geospatial) are unavailable.

## Configuration

The service can be configured using environment variables:

```bash
# Geocoding Service Configuration
GEOCODING_USER_AGENT=address-matching-service
GEOCODING_TIMEOUT=10

# Distance threshold for geospatial matching (in meters)
DISTANCE_THRESHOLD=50.0

# Feature toggles
USE_ML_MODEL=true
USE_GEOSPATIAL=true

# Rule-based filter thresholds
POSTAL_CODE_THRESHOLD=0.8
STREET_THRESHOLD=0.7
CITY_THRESHOLD=0.8
HOUSE_NUMBER_THRESHOLD=0.8
OVERALL_THRESHOLD=0.7

# Strict matching requirements
REQUIRE_POSTAL_CODE_MATCH=false
REQUIRE_CITY_MATCH=true
REQUIRE_STREET_MATCH=true

# ML Model configuration
ML_MODEL_PATH=address_matching_model.pkl

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
```

## Architecture

### Components

1. **AddressParser**: Normalizes and parses addresses into components
2. **FuzzyMatcher**: Computes similarity scores between address components
3. **RuleBasedFilter**: Applies configurable rules for matching decisions
4. **GeocodingService**: Provides geospatial validation using external APIs
5. **MLModel**: Machine learning model for entity resolution
6. **AddressMatcher**: Main orchestrator that combines all components

### Matching Process

1. **Address Parsing**: Extract and normalize address components
2. **Fuzzy Matching**: Compute similarity scores for each component
3. **Geospatial Validation**: Geocode addresses and calculate distance (optional)
4. **Rule-Based Filtering**: Apply configurable business rules
5. **ML Prediction**: Use trained model for final decision (optional)
6. **Final Decision**: Combine all signals into final match decision and confidence

### Decision Logic

The service uses a hierarchical decision process:

1. If rule-based filter rejects → No match (high precision)
2. If ML model available → Use ML prediction with geospatial adjustment
3. Fallback → Similarity-based decision with geospatial adjustment

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Full matching pipeline testing
- **Scenario Tests**: Real-world address matching scenarios
- **Performance Tests**: Response time validation

## Performance Considerations

### Optimization Features

- **Geocoding Cache**: LRU cache for repeated address lookups
- **Rate Limiting**: Respectful delays between geocoding requests
- **Fallback Modes**: Graceful degradation when services unavailable
- **Batch Processing**: Support for multiple address pairs

### Expected Performance

- **Response Time**: < 2 seconds per request (with geocoding)
- **Throughput**: ~30 requests/minute (limited by geocoding rate limits)
- **Memory Usage**: ~50MB base + ML model (~10MB)

## Deployment

### Docker Deployment

```bash
docker compose up --build -d
```

See the root `Dockerfile` and `docker-compose.yml` for the production image (Python 3.12-slim, non-root user, healthcheck).

### Production Considerations

1. **API Keys**: Configure geocoding service API keys for production use
2. **Rate Limiting**: Implement request rate limiting at the API gateway level
3. **Monitoring**: Add metrics collection and alerting
4. **Scaling**: Use multiple instances behind a load balancer
5. **Database**: Consider caching geocoding results in a database
6. **Security**: Implement authentication and input validation

## API Documentation

Full interactive API documentation is available at `/docs` when the service is running.

### Error Responses

The service returns appropriate HTTP status codes:

- **200**: Successful match operation
- **400**: Invalid request format
- **422**: Validation error
- **500**: Internal server error

Error response format:
```json
{
  "detail": "Error description"
}
```

## Extending the Service

### Adding New Rules

Add custom rules by extending the `RuleBasedFilter` class:

```python
class CustomRuleFilter(RuleBasedFilter):
    def apply_custom_rule(self, similarities, addr1, addr2):
        # Custom logic here
        return True
```

### Improving the ML Model

1. Collect real address matching data
2. Retrain the model with actual data
3. Add new features to the feature extraction
4. Experiment with different algorithms

### Adding New Geocoding Providers

Extend the `GeocodingService` to support multiple providers:

```python
class MultiProviderGeocodingService(GeocodingService):
    def __init__(self):
        self.providers = [NominatimProvider(), GoogleProvider()]
```

## Troubleshooting

### Common Issues

1. **Postal library installation fails**: 
   - Error: `fatal error: 'libpostal/libpostal.h' file not found`
   - Solution: Install libpostal system library first (see installation instructions above)
   - Alternative: Use the service without postal (fallback parser will be used)

2. **Geocoding failures**: 
   - Check internet connection and rate limits
   - Nominatim has usage policies - consider using API keys for production

3. **ML model errors**: 
   - Verify scikit-learn installation
   - Check if model file permissions are correct

4. **Performance issues**: 
   - Enable caching and check geocoding rate limits
   - Consider using minimal version for faster startup

5. **Docker build issues**:
   - Ensure Docker has network access to install pinned PyPI packages
   - Copy `.env.example` to `.env` and adjust settings as needed

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG python main.py
```

### Health Checks

Monitor component status:
```bash
curl http://localhost:8000/health
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Dependencies

### Core Dependencies

- **FastAPI**: Modern web framework for APIs
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server implementation

### Address Processing

- **postal**: Python bindings for libpostal (optional)
- **rapidfuzz**: Fast fuzzy string matching

### Geospatial

- **geopy**: Geocoding and geospatial calculations

### Machine Learning

- **scikit-learn**: ML algorithms and preprocessing
- **numpy**: Numerical computing
- **pandas**: Data manipulation

### Utilities

- **loguru**: Modern logging
- **python-dotenv**: Environment variable management

### Development

- **pytest**: Testing framework
- **pytest-asyncio**: Async testing support

## Acknowledgments

- libpostal for address parsing
- OpenStreetMap Nominatim for geocoding
- FastAPI community for the excellent framework 