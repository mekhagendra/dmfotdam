# Project Structure 

This document outlines the architecture and organization of the Terrorism Detection and Monitoring System.

## Directory Structure

```
dmfotdam/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── core/              # Core functionality
│   │   │   ├── config.py      # Configuration management
│   │   │   ├── database.py    # Database connection
│   │   │   ├── security.py    # Authentication & authorization
│   │   │   ├── logging.py     # Logging configuration
│   │   │   └── celery.py      # Background task management
│   │   ├── api/               # API endpoints
│   │   │   ├── endpoints/     # Route handlers
│   │   │   │   ├── auth.py    # Authentication endpoints
│   │   │   │   ├── upload.py  # File upload endpoints
│   │   │   │   ├── detection.py # Threat detection endpoints
│   │   │   │   └── monitoring.py # Live monitoring endpoints
│   │   │   └── dependencies.py # Dependency injection
│   │   ├── services/          # Business logic
│   │   │   ├── text_analyzer.py # Text analysis service
│   │   │   ├── ml_service.py    # Machine learning service
│   │   │   ├── web_scraper.py   # Web scraping service
│   │   │   └── live_monitor.py  # Live monitoring service
│   │   ├── models/            # Database models
│   │   │   ├── user.py        # User model
│   │   │   ├── document.py    # Document model
│   │   │   ├── analysis.py    # Analysis result model
│   │   │   └── alert.py       # Alert model
│   │   └── utils/             # Utility functions
│   │       ├── file_handler.py # File processing utilities
│   │       ├── text_processor.py # Text processing utilities
│   │       └── validators.py   # Input validation
│   ├── data/                  # Data storage
│   │   ├── uploads/           # Uploaded files
│   │   ├── models/            # ML model files
│   │   └── datasets/          # Training datasets
│   ├── tests/                 # Test files
│   ├── config/                # Configuration files
│   ├── main.py                # Application entry point
│   └── requirements.txt       # Python dependencies
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── common/        # Reusable components
│   │   │   ├── layout/        # Layout components
│   │   │   ├── forms/         # Form components
│   │   │   └── charts/        # Chart components
│   │   ├── pages/             # Page components
│   │   │   ├── Dashboard.tsx  # Main dashboard
│   │   │   ├── Upload.tsx     # File upload page
│   │   │   ├── Monitoring.tsx # Live monitoring page
│   │   │   └── Reports.tsx    # Analysis reports page
│   │   ├── services/          # API services
│   │   │   ├── api.ts         # API client configuration
│   │   │   ├── auth.service.ts # Authentication service
│   │   │   └── detection.service.ts # Detection service
│   │   ├── hooks/             # Custom React hooks
│   │   ├── context/           # React context providers
│   │   ├── utils/             # Utility functions
│   │   └── assets/            # Static assets
│   ├── public/                # Public files
│   └── package.json           # Node.js dependencies
├── docker/                    # Docker configuration
│   ├── docker-compose.yml     # Multi-container setup
│   ├── Dockerfile.backend     # Backend container
│   ├── Dockerfile.frontend    # Frontend container
│   └── nginx.conf             # Nginx configuration
├── docs/                      # Documentation
├── scripts/                   # Setup and utility scripts
├── .env.example              # Environment variables template
├── .gitignore               # Git ignore rules
└── README.md                # Project documentation
```

## Core Components

### Backend Services

1. **Text Analysis Service**
   - Document parsing (PDF, DOCX, TXT)
   - Natural language processing
   - Keyword extraction and sentiment analysis
   - Threat classification

2. **Machine Learning Service**
   - Pre-trained models for threat detection
   - Custom model training capabilities
   - Model versioning and management
   - Prediction pipeline

3. **Web Scraping Service**
   - Configurable web scrapers
   - Social media monitoring
   - News article collection
   - Data normalization

4. **Live Monitoring Service**
   - Real-time data processing
   - WebSocket connections for live updates
   - Alert generation and notification
   - Dashboard metrics

### Frontend Components

1. **Dashboard**
   - Real-time monitoring overview
   - Key metrics and statistics
   - Interactive charts and graphs
   - Recent alerts and activities

2. **File Upload Interface**
   - Drag-and-drop file upload
   - Multi-format support
   - Upload progress tracking
   - Batch processing capabilities

3. **Monitoring Console**
   - Live data streams
   - Configurable monitoring sources
   - Alert management
   - Historical data visualization

4. **Reports and Analytics**
   - Detailed analysis results
   - Exportable reports
   - Trend analysis
   - Pattern recognition insights

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for Python
- **SQLAlchemy**: SQL toolkit and ORM
- **PostgreSQL**: Relational database
- **Redis**: Caching and message broker
- **Celery**: Background task processing
- **NLTK/spaCy**: Natural language processing
- **Transformers**: Pre-trained NLP models
- **Scrapy/Selenium**: Web scraping

### Frontend
- **React**: JavaScript library for building user interfaces
- **TypeScript**: Typed superset of JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Chart.js/Recharts**: Data visualization
- **React Query**: Data fetching and caching
- **Socket.io**: Real-time communication

### Infrastructure
- **Docker**: Containerization
- **Nginx**: Reverse proxy and static file serving
- **Prometheus**: Monitoring and metrics
- **ELK Stack**: Logging and log analysis (optional)

## Security Considerations

1. **Authentication & Authorization**
   - JWT-based authentication
   - Role-based access control
   - API rate limiting

2. **Data Protection**
   - Encrypted data at rest
   - Secure file upload validation
   - Input sanitization

3. **Network Security**
   - HTTPS enforcement
   - CORS configuration
   - API endpoint protection

4. **Monitoring & Auditing**
   - Access logging
   - Security event monitoring
   - Anomaly detection