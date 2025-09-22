# SyncScope Analytics Service

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-development-orange.svg)](https://github.com/SyncScope-INTEC/syncscope-analytics-service)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Django Version](https://img.shields.io/badge/django-4.2+-green.svg)](https://djangoproject.com)

The **Analytics Service** is a core component of the SyncScope developer productivity monitoring platform. It provides comprehensive analytics, reporting, and data processing capabilities for developer productivity metrics, code quality analysis, and team collaboration insights.

## Features

### Analytics Engine
- **Real-time Metric Calculations**: Advanced productivity, code quality, and collaboration metrics
- **Statistical Analysis**: Comprehensive statistical processing with pandas and numpy
- **Trend Detection**: Time series analysis and pattern recognition
- **Anomaly Detection**: Automated detection of unusual patterns in developer behavior

### Report Generation
- **12 Report Types**: Productivity, code quality, team collaboration, performance, security, and more
- **Multiple Export Formats**: PDF, Excel, CSV, and JSON exports with professional formatting
- **Async Processing**: Non-blocking report generation for large datasets
- **Regeneration Support**: Refresh reports with latest data

### Data Integration
- **PostgreSQL**: Primary data storage with analytics schema
- **InfluxDB**: Time series metrics storage for high-frequency data
- **Redis**: Caching layer for performance optimization
- **Service Integration**: HTTP clients for Auth, Monitoring, and Management services

### Security & Performance
- **JWT Authentication**: Secure service-to-service communication
- **Rate Limiting**: API endpoint protection and abuse prevention
- **Caching Strategy**: Intelligent caching for metric calculations
- **Permission System**: Role-based access control

## Architecture

SyncScope follows a **Service-Based Architecture (SBA)** with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Auth Service  │    │ Monitoring Svc  │    │ Management Svc  │
│                 │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │              HTTP Integration              │
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                   ┌─────────────▼───────────────┐
                   │     Analytics Service       │
                   │                             │
                   │  ┌─────────────────────────┐│
                   │  │   Metric Calculators    ││
                   │  │   Report Generator      ││
                   │  │   Data Analysis Engine  ││
                   │  │   Export Functionality  ││
                   │  └─────────────────────────┘│
                   └─────────────────────────────┘
                                 │
                   ┌─────────────▼───────────────┐
                   │     Data Storage Layer      │
                   │                             │
                   │  PostgreSQL │ InfluxDB │Redis│
                   └─────────────────────────────┘
```

## Technology Stack

- **Framework**: Django 4.2+ with Django REST Framework
- **Language**: Python 3.11+
- **Databases**:
  - PostgreSQL (primary data storage)
  - InfluxDB (time series metrics)
  - Redis (caching)
- **Analytics**: pandas, numpy, scikit-learn
- **Documentation**: drf-spectacular (OpenAPI 3.0)
- **Export**: ReportLab (PDF), openpyxl (Excel)
- **Deployment**: Docker, Railway Platform

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- InfluxDB 2.0+
- Git

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/SyncScope-INTEC/syncscope-analytics-service.git
cd syncscope-analytics-service
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 4. Set Up Database
```bash
# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 5. Start Development Server
```bash
python manage.py runserver
```

The service will be available at `http://localhost:8000`

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEBUG` | Enable debug mode | `False` | No |
| `SECRET_KEY` | Django secret key | - | Yes |
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` | No |
| `INFLUXDB_URL` | InfluxDB server URL | `http://localhost:8086` | No |
| `INFLUXDB_TOKEN` | InfluxDB access token | - | Yes |
| `INFLUXDB_ORG` | InfluxDB organization | - | Yes |
| `INFLUXDB_BUCKET` | InfluxDB bucket name | - | Yes |
| `AUTH_SERVICE_URL` | Auth service endpoint | - | Yes |
| `MONITORING_SERVICE_URL` | Monitoring service endpoint | - | Yes |
| `MANAGEMENT_SERVICE_URL` | Management service endpoint | - | Yes |

### Database Configuration

The service uses a multi-database setup:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'options': '-c search_path=analytics,public'
        }
    }
}
```

## API Reference

### Core Endpoints

#### Reports
- `GET /api/reports/` - List reports
- `POST /api/reports/` - Create new report
- `GET /api/reports/{id}/` - Get report details
- `POST /api/reports/{id}/export/` - Export report
- `POST /api/reports/{id}/regenerate/` - Regenerate report

#### Metrics
- `GET /api/metrics/` - List metric definitions
- `POST /api/metrics/` - Create metric definition
- `POST /api/calculate/` - Calculate specific metric

#### Analytics
- `GET /api/dashboard/` - Get dashboard data

#### Health & Documentation
- `GET /health/` - Health check
- `GET /api/docs/` - Interactive API documentation
- `GET /api/schema/` - OpenAPI schema

### Example Requests

#### Create a Productivity Report
```bash
curl -X POST http://localhost:8000/api/reports/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "January Productivity Report",
    "type": "productivity",
    "config": {
      "start_date": "2024-01-01",
      "end_date": "2024-01-31",
      "include_weekends": false
    }
  }'
```

#### Export Report as PDF
```bash
curl -X POST http://localhost:8000/api/reports/123/export/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "pdf",
    "include_charts": true,
    "detailed": false
  }' \
  --output report.pdf
```

#### Calculate Productivity Metric
```bash
curl -X POST http://localhost:8000/api/calculate/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metric_name": "productivity",
    "context": {
      "user_id": "user-123",
      "start_date": "2024-01-01",
      "end_date": "2024-01-31"
    }
  }'
```

## Analytics Features

### Metric Calculators

The service includes 10 comprehensive metric calculators:

1. **Productivity Metrics**
   - Session duration and frequency
   - Commit patterns and frequency
   - Code output measurements
   - Time-based productivity scoring

2. **Code Quality Metrics**
   - Complexity analysis
   - Test coverage assessment
   - Code duplication detection
   - Security vulnerability scanning

3. **Team Collaboration Metrics**
   - Pull request reviews
   - Code comments and discussions
   - Meeting participation
   - Knowledge sharing indicators

4. **Performance Metrics**
   - Build and deployment times
   - Application performance
   - Resource utilization
   - Optimization opportunities

5. **Security Metrics**
   - Vulnerability assessments
   - Security practice compliance
   - Risk factor analysis
   - Security training completion

### Report Types

- **Productivity Reports**: Individual and team productivity analysis
- **Code Quality Reports**: Code health and quality metrics
- **Team Collaboration Reports**: Team dynamics and collaboration patterns
- **Performance Reports**: System and application performance analysis
- **Security Reports**: Security posture and compliance status
- **Efficiency Reports**: Resource utilization and optimization
- **Engagement Reports**: Developer engagement and satisfaction
- **Learning Reports**: Skill development and training progress
- **Deployment Reports**: Deployment frequency and success rates
- **Innovation Reports**: Innovation metrics and R&D activities
- **Burnout Analysis Reports**: Developer wellbeing indicators
- **Custom Reports**: Configurable reports with custom metrics

### Data Analysis Capabilities

- **Statistical Analysis**: Comprehensive statistical processing
- **Trend Detection**: Time series analysis and pattern recognition
- **Anomaly Detection**: Automated outlier and anomaly identification
- **Correlation Analysis**: Relationship analysis between metrics
- **Predictive Modeling**: ML-based predictions and forecasting
- **Data Visualization**: Chart and graph generation for reports

## Testing

### Running Tests
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=apps --cov-report=html

# Run specific test file
python -m pytest tests/test_models.py

# Run with verbose output
python -m pytest -v
```

### Test Structure
```
tests/
├── __init__.py
├── conftest.py              # Test configuration and fixtures
├── test_models.py           # Model tests
├── test_views.py            # API endpoint tests
├── test_metric_calculators.py  # Metric calculation tests
├── test_data_analysis.py    # Data analysis tests
├── test_influxdb_client.py  # InfluxDB integration tests
├── test_health.py           # Health check tests
└── test_service_integration.py  # External service tests
```

### Test Coverage

The test suite provides comprehensive coverage:
- **Models**: Database model functionality and validation
- **Views**: API endpoint behavior and authentication
- **Metric Calculators**: All metric calculation algorithms
- **Data Analysis**: Statistical and analytical functions
- **InfluxDB Integration**: Time series data operations
- **Health Checks**: Service health monitoring
- **Service Integration**: External service communication

Target coverage: **90%+**

## Deployment

### Docker Deployment

1. **Build the image**:
```bash
docker build -t syncscope-analytics-service .
```

2. **Run with environment variables**:
```bash
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/analytics_db \
  -e REDIS_URL=redis://redis:6379 \
  -e INFLUXDB_URL=http://influxdb:8086 \
  syncscope-analytics-service
```

### Railway Deployment

1. **Connect repository** to Railway
2. **Set environment variables** in Railway dashboard
3. **Deploy** automatically on push to main branch

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure secure `SECRET_KEY`
- [ ] Set up proper database with connection pooling
- [ ] Configure Redis for caching
- [ ] Set up InfluxDB for time series data
- [ ] Configure external service URLs
- [ ] Set up SSL/TLS certificates
- [ ] Configure monitoring and logging
- [ ] Set up backup strategy
- [ ] Configure rate limiting
- [ ] Test health check endpoints

## Monitoring & Observability

### Health Checks

The service provides comprehensive health monitoring:

```bash
curl http://localhost:8000/health/
```

Response format:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "database": true,
  "redis": true,
  "influxdb": true,
  "external_services": {
    "auth_service": true,
    "monitoring_service": true,
    "management_service": true
  }
}
```

### Metrics & Logging

- **Application Metrics**: Performance and usage metrics
- **Business Metrics**: Analytics calculation performance
- **Error Tracking**: Comprehensive error logging and tracking
- **Performance Monitoring**: Response times and resource usage

## Development

### Project Structure
```
syncscope-analytics-service/
├── apps/
│   └── analytics/
│       ├── models.py           # Database models
│       ├── views.py            # API views
│       ├── serializers.py      # DRF serializers
│       ├── urls.py             # URL routing
│       ├── metric_calculators.py  # Metric calculation engine
│       ├── data_analysis.py    # Data analysis utilities
│       ├── influxdb_client.py  # InfluxDB integration
│       ├── service_integration.py  # External service clients
│       ├── authentication.py   # JWT authentication
│       ├── middleware.py       # Custom middleware
│       ├── health.py           # Health check functions
│       └── db_mixins.py        # Database mixins
├── config/
│   ├── settings.py            # Django settings
│   ├── urls.py                # Root URL configuration
│   └── database_retry.py      # Database retry logic
├── tests/                     # Comprehensive test suite
├── .github/                   # GitHub Actions workflows
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container configuration
├── .dockerignore             # Docker ignore file
└── README.md                 # This file
```

### Coding Standards

- **Python**: Follow PEP 8 style guide
- **Django**: Follow Django best practices
- **API Design**: RESTful API principles
- **Testing**: Minimum 90% test coverage
- **Documentation**: Comprehensive docstrings and comments

### Git Workflow

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature-name`
3. **Commit** your changes: `git commit -am 'Add some feature'`
4. **Push** to the branch: `git push origin feature/your-feature-name`
5. **Submit** a pull request

### Code Review Process

- All changes require peer review
- Automated CI/CD checks must pass
- Test coverage must be maintained
- Documentation must be updated

## Documentation

### API Documentation
- **Interactive Docs**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

### Additional Resources
- [Architecture Overview](docs/architecture.md)
- [API Examples](docs/api-examples.md)
- [Deployment Guide](docs/deployment.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database connectivity
python manage.py dbshell

# Verify migrations
python manage.py showmigrations
```

#### InfluxDB Connection Issues
```bash
# Test InfluxDB connectivity
curl http://localhost:8086/health

# Check InfluxDB configuration
python manage.py shell
>>> from apps.analytics.influxdb_client import influxdb_manager
>>> influxdb_manager.health_check()
```

#### Redis Connection Problems
```bash
# Test Redis connectivity
redis-cli ping

# Check Redis configuration
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> cache.get('test')
```

#### External Service Connectivity
```bash
# Test service endpoints
curl http://auth-service-url/health/
curl http://monitoring-service-url/health/
curl http://management-service-url/health/
```

### Performance Issues

- **Slow Report Generation**: Check InfluxDB query performance and Redis caching
- **High Memory Usage**: Monitor pandas DataFrame operations and memory optimization
- **Database Timeouts**: Verify connection pooling and query optimization

### Debugging

```bash
# Enable debug mode
export DEBUG=True

# Run with verbose logging
python manage.py runserver --verbosity=2

# Check logs
tail -f logs/analytics.log
```

## Changelog

### v1.0.0 (2024-01-01)
- Initial release
- Complete analytics engine implementation
- 12 comprehensive report types
- Multi-format export capabilities
- InfluxDB integration for time series data
- Comprehensive test suite (90%+ coverage)
- Full CI/CD pipeline with GitHub Actions

### Upcoming Features
- Machine learning predictions
- Advanced anomaly detection
- Real-time dashboards
- Mobile API endpoints
- Enhanced visualization capabilities

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **SyncScope Team** for architecture guidance and requirements
- **Django Community** for the excellent framework
- **pandas/numpy Teams** for powerful data analysis tools
- **InfluxDB Team** for time series database capabilities

## Support

For support, please contact:
- **Email**: support@syncscope.dev
- **Issues**: [GitHub Issues](https://github.com/SyncScope-INTEC/syncscope-analytics-service/issues)
- **Documentation**: [Official Docs](https://docs.syncscope.dev)

---

**Built by the SyncScope Team**
