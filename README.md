# Terrorism Detection and Monitoring System (TDM)

A comprehensive web data mining application for terrorism detection and monitoring, designed to analyze documents and provide real-time threat monitoring capabilities.

## Overview

The TDM System is a sophisticated platform that combines machine learning, natural language processing, and web scraping technologies to detect potential security threats from various data sources. The system supports both document upload analysis and live monitoring of online content.

### Key Features

- **Document Analysis**: Upload and analyze documents (PDF, DOCX, TXT) for threat detection
- **Live Monitoring**: Real-time monitoring of web sources and social media
- **AI-Powered Detection**: Advanced NLP and ML models for threat classification
- **Interactive Dashboard**: Real-time visualization of threats and analytics
- **Alert System**: Automated alerting for detected threats
- **Reporting**: Comprehensive analysis reports and trend visualization
- **Security-First**: Built with enterprise-security standards

## Architecture

### System Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Frontend │────│   FastAPI Backend │────│  ML/NLP Engine  │
│   (Dashboard)    │    │   (REST API)     │    │  (TensorFlow)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   PostgreSQL     │    │   Redis Cache   │
│   (User Interface│    │   (Database)     │    │   (Background)  │
│   & Visualizations)   │                  │    │   (Tasks)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Technology Stack

**Backend (Python)**
- FastAPI - Modern, fast web framework
- SQLAlchemy - Database ORM
- PostgreSQL - Primary database
- Redis - Caching and task queue
- Celery - Background task processing
- NLTK/spaCy - Natural language processing
- Transformers - Pre-trained ML models
- Scrapy/Selenium - Web scraping

**Frontend (React)**
- React 18 with TypeScript
- Tailwind CSS - Styling framework
- Chart.js/Recharts - Data visualization
- React Query - Data fetching
- Socket.io - Real-time updates

**Infrastructure**
- Docker & Docker Compose
- Nginx - Reverse proxy
- Prometheus - Monitoring (optional)

## Project Structure

```
dmfotdam/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── core/              # Core functionality (config, db, auth)
│   │   ├── api/               # API endpoints and routes
│   │   ├── services/          # Business logic services
│   │   ├── models/            # Database models
│   │   └── utils/             # Utility functions
│   ├── data/                  # Data storage
│   │   ├── uploads/           # Uploaded files
│   │   ├── models/            # ML model files
│   │   └── datasets/          # Training datasets
│   ├── tests/                 # Backend tests
│   ├── main.py               # Application entry point
│   └── requirements.txt      # Python dependencies
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API services
│   │   ├── hooks/           # Custom React hooks
│   │   └── utils/           # Frontend utilities
│   └── package.json         # Node.js dependencies
├── docker/                   # Docker configuration
│   ├── docker-compose.yml    # Multi-container setup
│   ├── Dockerfile.backend    # Backend container
│   └── Dockerfile.frontend   # Frontend container
├── docs/                     # Documentation
├── scripts/                  # Setup and utility scripts
└── README.md                # This file
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 13+
- Redis 6+

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dmfotdam
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs

### Option 2: Manual Setup

1. **Setup Backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Configure database and environment
   cp ../.env.example .env
   
   # Run migrations (when available)
   python main.py
   ```

2. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   npm start
   ```

### Option 3: Quick Setup Script

```bash
# Make script executable
chmod +x scripts/setup.sh

# Run setup script
./scripts/setup.sh

# Start development servers
./scripts/start-dev.sh
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory based on `.env.example`:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/tdm_db

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External APIs (Optional)
NEWS_API_KEY=your-news-api-key
TWITTER_BEARER_TOKEN=your-twitter-token

# Redis
REDIS_URL=redis://localhost:6379/0

# File Upload
MAX_FILE_SIZE=52428800  # 50MB
UPLOAD_DIR=data/uploads
```

### Database Setup

The system uses PostgreSQL as the primary database. The schema includes:

- **Users**: Authentication and user management
- **Documents**: Uploaded document metadata
- **Analyses**: Analysis results and scores
- **Alerts**: Generated security alerts
- **Sources**: Monitoring source configuration

## Usage

### Document Analysis

1. **Upload Documents**
   - Navigate to the Upload page
   - Drag and drop or select files (PDF, DOCX, TXT)
   - Wait for processing completion

2. **View Results**
   - Check the analysis results on the dashboard
   - Review threat scores and classifications
   - Export detailed reports

### Live Monitoring

1. **Configure Sources**
   - Set up monitoring sources (URLs, social media)
   - Configure keywords and filters
   - Set alert thresholds

2. **Monitor Dashboard**
   - Real-time threat detection updates
   - Live data visualization
   - Alert notifications

### API Usage

The system provides a RESTful API for integration:

```bash
# Authenticate
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username":"user","password":"pass"}'

# Upload document
curl -X POST "http://localhost:8000/api/v1/upload/document" \
     -H "Authorization: Bearer <token>" \
     -F "file=@document.pdf"

# Get results
curl -X GET "http://localhost:8000/api/v1/detection/results/<analysis_id>" \
     -H "Authorization: Bearer <token>"
```

## Security Considerations

### Data Protection
- All uploaded files are scanned and validated
- Sensitive data is encrypted at rest
- User sessions are secured with JWT tokens
- Role-based access control (RBAC)

### Privacy Compliance
- Personal data is anonymized where required
- GDPR compliance features built-in
- Audit logging for all actions
- Data retention policies configurable

### Network Security
- HTTPS enforced in production
- CORS properly configured
- API rate limiting implemented
- Input validation and sanitization

## Testing

### Backend Tests
```bash
cd backend
source venv/bin/activate
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
# Run with Docker Compose
docker-compose -f docker/docker-compose.test.yml up --abort-on-container-exit
```

## Performance

### Optimization Features
- Redis caching for frequent queries
- Background task processing with Celery
- Database connection pooling
- Frontend code splitting and lazy loading
- CDN integration ready

### Monitoring
- Health check endpoints
- Prometheus metrics (optional)
- Application logging
- Error tracking

## Deployment

### Production Deployment

1. **Prepare Environment**
   ```bash
   # Update environment variables for production
   export ENVIRONMENT=production
   export DATABASE_URL=your-production-db-url
   ```

2. **Deploy with Docker**
   ```bash
   docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
   ```

3. **Setup Reverse Proxy**
   - Configure Nginx for SSL termination
   - Set up domain and SSL certificates
   - Configure load balancing if needed

### Scaling Considerations
- Horizontal scaling with multiple backend instances
- Database read replicas for better performance
- CDN for static assets
- Container orchestration with Kubernetes

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use ESLint and Prettier for JavaScript/TypeScript
- Write unit tests for new features
- Update documentation for API changes

## Documentation

- [Project Structure](docs/project-structure.md) - Detailed architecture overview
- [API Documentation](docs/api-documentation.md) - Complete API reference
- [Development Guide](docs/development.md) - Development setup and guidelines
- [Deployment Guide](docs/deployment.md) - Production deployment instructions

## Legal Notice

This system is designed for legitimate security research and threat monitoring purposes only. Users must:

- Comply with all applicable laws and regulations
- Respect privacy rights and data protection laws  
- Use the system ethically and responsibly
- Obtain proper authorization for monitoring activities

The developers are not responsible for any misuse of this software.

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check Python version (3.11+ required)
- Verify database connection
- Check environment variables

**Frontend build fails:**
- Clear node_modules and reinstall
- Check Node.js version (18+ required)
- Verify API endpoints configuration

**Database connection issues:**
- Verify PostgreSQL is running
- Check connection string format
- Ensure database exists

### Getting Help

- Check the [Issues](issues) page for known problems
- Review the documentation in the [docs](docs) directory
- Contact the development team

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- FastAPI team for the excellent web framework
- React team for the frontend library  
- The open-source NLP and ML communities
- Security researchers and threat intelligence community

---

