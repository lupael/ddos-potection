# Development Guide

This guide helps developers set up their local development environment and contribute to the DDoS Protection Platform.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Git

### Local Environment Setup

#### 1. Clone Repository

```bash
git clone https://github.com/i4edubd/ddos-potection.git
cd ddos-potection
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://ddos_user:ddos_pass@localhost:5432/ddos_platform
REDIS_HOST=localhost
REDIS_PORT=6379
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True
EOF

# Start PostgreSQL and Redis (if not using Docker)
# Create database
createdb ddos_platform

# Run migrations (if using Alembic)
alembic upgrade head

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file
echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env.local

# Start development server
npm start
```

The frontend will open at http://localhost:3000 and the API at http://localhost:8000

## Project Structure

```
ddos-potection/
├── backend/
│   ├── models/          # Database models
│   ├── routers/         # API route handlers
│   ├── services/        # Business logic services
│   ├── config.py        # Configuration
│   ├── database.py      # Database connection
│   ├── main.py          # FastAPI application
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── public/          # Static files
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API client
│   │   └── styles/      # CSS files
│   └── package.json     # Node dependencies
├── scripts/             # Integration scripts
├── docker/              # Docker configurations
├── docs/                # Documentation
└── docker-compose.yml   # Docker Compose config
```

## Backend Development

### Adding a New API Endpoint

1. Create or update a router file in `backend/routers/`
2. Define the endpoint using FastAPI decorators
3. Include the router in `main.py`

Example:

```python
# backend/routers/example_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter()

@router.get("/example")
async def get_example(db: Session = Depends(get_db)):
    return {"message": "Hello World"}
```

```python
# backend/main.py
from routers import example_router

app.include_router(example_router.router, prefix="/api/v1/example", tags=["Example"])
```

### Adding a New Database Model

1. Create the model in `backend/models/models.py`
2. Run migration if using Alembic

```python
from sqlalchemy import Column, Integer, String
from database import Base

class Example(Base):
    __tablename__ = "examples"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
```

### Adding a New Service

Create service files in `backend/services/`:

```python
# backend/services/example_service.py
from database import SessionLocal

class ExampleService:
    def __init__(self):
        pass
    
    def process_data(self, data):
        # Business logic here
        pass

def main():
    service = ExampleService()
    service.process_data({})

if __name__ == "__main__":
    main()
```

## Frontend Development

### Adding a New Page

1. Create page component in `frontend/src/pages/`
2. Add route in `App.js`

```javascript
// frontend/src/pages/NewPage.js
import React from 'react';
import Navbar from '../components/Navbar';

function NewPage() {
  return (
    <>
      <Navbar />
      <div className="container">
        <h1>New Page</h1>
      </div>
    </>
  );
}

export default NewPage;
```

```javascript
// frontend/src/App.js
import NewPage from './pages/NewPage';

// Add route
<Route path="/new" element={
  <PrivateRoute>
    <NewPage />
  </PrivateRoute>
} />
```

### Adding API Service

Update `frontend/src/services/api.js`:

```javascript
export const exampleService = {
  list: () => api.get('/example/'),
  create: (data) => api.post('/example/', data),
  get: (id) => api.get(`/example/${id}`),
};
```

### Styling Components

Use the existing CSS classes in `frontend/src/styles/App.css` or add new ones:

```css
.custom-class {
  background: #f0f0f0;
  padding: 1rem;
  border-radius: 8px;
}
```

## Testing

### Backend Tests

```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

Example test:

```python
# backend/tests/test_api.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage
```

Example test:

```javascript
// frontend/src/App.test.js
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders login page', () => {
  render(<App />);
  const element = screen.getByText(/DDoS Protection Platform/i);
  expect(element).toBeInTheDocument();
});
```

## Code Style

### Python (Backend)

Follow PEP 8 style guide:

```bash
# Install linting tools
pip install black flake8 isort

# Format code
black .

# Check style
flake8 .

# Sort imports
isort .
```

### JavaScript (Frontend)

Use Prettier and ESLint:

```bash
# Install tools
npm install --save-dev prettier eslint

# Format code
npx prettier --write "src/**/*.{js,jsx,json,css}"

# Lint code
npx eslint src/
```

## Database Migrations

Using Alembic for database migrations:

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Debugging

### Backend Debugging

Add breakpoints in your IDE or use pdb:

```python
import pdb; pdb.set_trace()
```

### Frontend Debugging

Use browser DevTools and React Developer Tools extension.

## Performance Optimization

### Backend

- Use async/await for I/O operations
- Implement caching with Redis
- Use database connection pooling
- Add pagination for large datasets
- Use background tasks for long operations

### Frontend

- Implement code splitting
- Use React.memo for expensive components
- Lazy load routes
- Optimize images
- Minimize bundle size

## Docker Development

### Build and Test Locally

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Debug Container

```bash
# Execute command in container
docker-compose exec backend bash

# View container logs
docker logs ddos-backend

# Inspect container
docker inspect ddos-backend
```

## Contributing Guidelines

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Write tests** for new functionality
4. **Follow code style** guidelines
5. **Commit changes**: `git commit -m 'Add amazing feature'`
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Request review from maintainers

## Common Issues

### Database Connection Error

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check database exists
psql -l | grep ddos_platform

# Recreate database
dropdb ddos_platform
createdb ddos_platform
```

### Redis Connection Error

```bash
# Check Redis is running
redis-cli ping

# Restart Redis
sudo systemctl restart redis
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Module Not Found

```bash
# Backend
pip install -r requirements.txt

# Frontend
npm install
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/docs/)
- [Docker Documentation](https://docs.docker.com/)

## Getting Help

- GitHub Issues: https://github.com/i4edubd/ddos-potection/issues
- Discord: [Join our server]
- Email: dev@example.com
