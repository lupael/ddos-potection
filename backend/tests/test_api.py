import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint returns correct information"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "DDoS Protection Platform API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "operational"

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_register_user():
    """Test user registration"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "isp_name": "Test ISP",
        "role": "admin"
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login():
    """Test user login"""
    # First register a user
    user_data = {
        "username": "logintest",
        "email": "logintest@example.com",
        "password": "testpassword123",
        "isp_name": "Test ISP",
        "role": "admin"
    }
    client.post("/api/v1/auth/register", json=user_data)
    
    # Then try to login
    login_data = {
        "username": "logintest",
        "password": "testpassword123"
    }
    response = client.post("/api/v1/auth/token", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/auth/token", data=login_data)
    assert response.status_code == 401

def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token"""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

def test_protected_endpoint_with_token():
    """Test accessing protected endpoint with valid token"""
    # Register and login
    user_data = {
        "username": "protectedtest",
        "email": "protected@example.com",
        "password": "testpassword123",
        "isp_name": "Test ISP",
        "role": "admin"
    }
    register_response = client.post("/api/v1/auth/register", json=user_data)
    token = register_response.json()["access_token"]
    
    # Access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "protectedtest"
    assert data["email"] == "protected@example.com"

def test_create_rule():
    """Test creating a firewall rule"""
    # Register and login
    user_data = {
        "username": "ruletest",
        "email": "rule@example.com",
        "password": "testpassword123",
        "isp_name": "Test ISP",
        "role": "admin"
    }
    register_response = client.post("/api/v1/auth/register", json=user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create rule
    rule_data = {
        "name": "Test Rule",
        "rule_type": "ip_block",
        "condition": {"ip": "1.2.3.4"},
        "action": "block",
        "priority": 100
    }
    response = client.post("/api/v1/rules/", json=rule_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Rule"
    assert data["rule_type"] == "ip_block"
    assert data["action"] == "block"

def test_list_rules():
    """Test listing firewall rules"""
    # Register and login
    user_data = {
        "username": "listtest",
        "email": "list@example.com",
        "password": "testpassword123",
        "isp_name": "Test ISP",
        "role": "admin"
    }
    register_response = client.post("/api/v1/auth/register", json=user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # List rules
    response = client.get("/api/v1/rules/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_traffic_stats():
    """Test getting traffic statistics"""
    # Register and login
    user_data = {
        "username": "traffictest",
        "email": "traffic@example.com",
        "password": "testpassword123",
        "isp_name": "Test ISP",
        "role": "admin"
    }
    register_response = client.post("/api/v1/auth/register", json=user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get traffic stats
    response = client.get("/api/v1/traffic/realtime", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_packets" in data
    assert "total_bytes" in data
    assert "total_flows" in data

def test_alert_summary():
    """Test getting alert summary"""
    # Register and login
    user_data = {
        "username": "alerttest",
        "email": "alert@example.com",
        "password": "testpassword123",
        "isp_name": "Test ISP",
        "role": "admin"
    }
    register_response = client.post("/api/v1/auth/register", json=user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get alert summary
    response = client.get("/api/v1/alerts/stats/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "by_status" in data
    assert "by_severity" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
