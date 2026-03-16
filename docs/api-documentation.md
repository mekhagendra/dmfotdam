# API Documentation

## Base URL
- Development: `http://localhost:8000/api/v1`
- Production: `https://your-domain.com/api/v1`

## Authentication
All protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - User logout

### File Upload
- `POST /upload/document` - Upload document for analysis
- `GET /upload/status/{task_id}` - Check upload/analysis status
- `GET /upload/history` - Get upload history

### Threat Detection
- `POST /detection/analyze-text` - Analyze text content
- `POST /detection/analyze-document` - Analyze uploaded document
- `GET /detection/results/{analysis_id}` - Get analysis results
- `GET /detection/reports` - List analysis reports

### Live Monitoring
- `POST /monitoring/sources` - Configure monitoring sources
- `GET /monitoring/sources` - List monitoring sources
- `GET /monitoring/alerts` - Get recent alerts
- `WebSocket /monitoring/live` - Real-time monitoring stream

### Dashboard
- `GET /dashboard/metrics` - Get dashboard metrics
- `GET /dashboard/trends` - Get trend data
- `GET /dashboard/summary` - Get summary statistics

## Response Format
All API responses follow this structure:
```json
{
  "success": true,
  "data": {...},
  "message": "Operation completed successfully",
  "timestamp": "2024-03-17T10:00:00Z"
}
```

## Error Handling
Error responses include:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {...}
  },
  "timestamp": "2024-03-17T10:00:00Z"
}
```