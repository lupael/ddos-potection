# Multi-ISP Support - Setup and Deployment Guide

This guide provides step-by-step instructions for deploying the Multi-ISP support features.

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL 15+
- Redis 7+
- Python 3.11+
- Active accounts with payment gateway providers (Stripe, PayPal, bKash)

## Quick Start

### 1. Update Environment Variables

Create or update your `.env` file with payment gateway credentials:

```bash
# Database Configuration
DATABASE_URL=postgresql://ddos_user:ddos_pass@postgres:5432/ddos_platform

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# JWT Configuration
SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key

# PayPal Configuration (Optional)
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_MODE=sandbox  # or 'live' for production

# bKash Configuration (Optional)
BKASH_APP_KEY=your_bkash_app_key
BKASH_APP_SECRET=your_bkash_app_secret
BKASH_USERNAME=your_bkash_username
BKASH_PASSWORD=your_bkash_password
BKASH_BASE_URL=https://tokenized.sandbox.bka.sh  # or production URL

# Report Storage
REPORTS_DIR=/app/reports

# API Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 2. Run Database Migration

The migration will create new tables and update existing ones:

```bash
# Using Docker
docker-compose exec backend python migrations/multi_isp_support_migration.py

# Or directly with Python
cd backend
python migrations/multi_isp_support_migration.py
```

To verify the migration:
```bash
python migrations/multi_isp_support_migration.py verify
```

To rollback (if needed):
```bash
python migrations/multi_isp_support_migration.py rollback
```

### 3. Start the Services

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Verify services are running
docker-compose ps
```

### 4. Test the API

Access the interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Payment Gateway Setup

### Stripe Setup

1. **Create Stripe Account**
   - Sign up at https://stripe.com
   - Get your API keys from the Dashboard

2. **Configure Webhook**
   - Go to Stripe Dashboard → Developers → Webhooks
   - Add endpoint: `https://your-domain.com/api/v1/payments/stripe/webhook`
   - Select events to listen for:
     - `payment_intent.succeeded`
     - `payment_intent.payment_failed`
   - Copy the webhook signing secret

3. **Test Stripe Integration**
   ```bash
   curl -X POST http://localhost:8000/api/v1/payments/stripe/create-payment-intent \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"amount": 29.99, "subscription_id": 1}'
   ```

4. **Use Test Cards** (in test mode):
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`

### PayPal Setup (Optional)

1. **Create PayPal Developer Account**
   - Sign up at https://developer.paypal.com
   - Create a REST API app to get credentials

2. **Implementation Notes**
   - The current implementation is a placeholder
   - Full integration requires the PayPal SDK
   - Install: `pip install paypalrestsdk`

3. **Example Integration Code** (to be added):
   ```python
   import paypalrestsdk
   
   paypalrestsdk.configure({
       "mode": os.environ.get("PAYPAL_MODE", "sandbox"),
       "client_id": os.environ.get("PAYPAL_CLIENT_ID"),
       "client_secret": os.environ.get("PAYPAL_CLIENT_SECRET")
   })
   ```

### bKash Setup (Optional)

1. **Get bKash Credentials**
   - Contact bKash for merchant account
   - Get app key, app secret, username, and password

2. **Implementation Notes**
   - Current implementation is a placeholder
   - Full integration requires bKash API calls
   - API documentation: https://developer.bka.sh/docs

## User Management

### Creating Users

Admin users can create new users within their ISP:

```bash
curl -X POST http://localhost:8000/api/v1/isp/users \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "email": "operator@example.com",
    "password": "secure_password",
    "role": "operator"
  }'
```

### Roles and Permissions

- **Admin**: Full access
  - User management
  - Subscription management
  - Payment processing
  - All CRUD operations

- **Operator**: Limited admin access
  - Create/modify rules
  - View alerts
  - Generate reports
  - Cannot manage users or subscriptions

- **Viewer**: Read-only access
  - View dashboards
  - View alerts
  - Download reports
  - Cannot modify anything

## Subscription Management

### List Available Plans

```bash
curl http://localhost:8000/api/v1/subscriptions/plans \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Subscription

```bash
curl -X POST http://localhost:8000/api/v1/subscriptions/subscribe \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_name": "professional",
    "billing_cycle": "monthly"
  }'
```

### Upgrade Subscription

```bash
curl -X PUT http://localhost:8000/api/v1/subscriptions/upgrade?new_plan=enterprise \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## Report Generation

### Generate PDF Report

```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate?report_type=monthly&file_format=pdf" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Generate CSV Report

```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate?report_type=weekly&file_format=csv" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Download Report

```bash
curl -X GET http://localhost:8000/api/v1/reports/123/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output report.pdf
```

## Production Deployment

### 1. Security Checklist

- [ ] Use strong, unique SECRET_KEY
- [ ] Enable HTTPS/TLS for all endpoints
- [ ] Use production payment gateway credentials
- [ ] Configure proper CORS settings
- [ ] Set DEBUG=false
- [ ] Use strong database passwords
- [ ] Enable database connection pooling
- [ ] Set up database backups
- [ ] Configure rate limiting
- [ ] Enable logging and monitoring

### 2. Database Configuration

For production, use connection pooling:

```python
# In database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### 3. Report Storage

Use persistent storage for reports:

**Docker Volume:**
```yaml
volumes:
  - reports_data:/app/reports
```

**S3/Cloud Storage:**
- Update reports router to use boto3 for S3
- Or use GCS, Azure Blob Storage

### 4. Monitoring Setup

Configure Prometheus metrics:
- Track payment success/failure rates
- Monitor subscription creation/cancellation
- Track report generation times

### 5. Backup Strategy

**Database Backups:**
```bash
# Daily backup
pg_dump -U ddos_user ddos_platform > backup_$(date +%Y%m%d).sql

# Automated with cron
0 2 * * * /path/to/backup_script.sh
```

**Report Files:**
- Use cloud storage with versioning
- Keep 90 days of reports
- Archive older reports

## Troubleshooting

### Common Issues

**1. Migration Fails**
```bash
# Check database connection
psql -U ddos_user -d ddos_platform -h localhost

# Verify table structure
\dt

# Re-run migration
python migrations/multi_isp_support_migration.py
```

**2. Stripe Webhook Not Working**
- Verify webhook secret is correct
- Check HTTPS is enabled
- Test with Stripe CLI:
  ```bash
  stripe listen --forward-to localhost:8000/api/v1/payments/stripe/webhook
  ```

**3. Report Generation Fails**
- Check REPORTS_DIR exists and is writable
- Verify fpdf2 is installed
- Check disk space

**4. Permission Denied Errors**
- Verify user role is correct
- Check JWT token is valid
- Ensure ISP ID matches

## Testing

Run the test suite:

```bash
# Run all tests
pytest backend/tests/test_multi_isp_support.py -v

# Run specific test
pytest backend/tests/test_multi_isp_support.py::TestSubscriptionRouter::test_create_subscription_valid_plan -v

# With coverage
pytest backend/tests/test_multi_isp_support.py --cov=backend/routers --cov-report=html
```

## API Examples

See the full API documentation in `docs/MULTI_ISP_FEATURES.md`

### Complete Workflow Example

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. Register and login
register_response = requests.post(f"{BASE_URL}/auth/register", json={
    "username": "admin",
    "email": "admin@isp.com",
    "password": "secure_pass",
    "isp_name": "MyISP",
    "role": "admin"
})
token = register_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Create subscription
subscription = requests.post(
    f"{BASE_URL}/subscriptions/subscribe",
    headers=headers,
    json={"plan_name": "professional", "billing_cycle": "monthly"}
)

# 3. Create payment
payment = requests.post(
    f"{BASE_URL}/payments/stripe/create-payment-intent",
    headers=headers,
    json={"amount": 99.99, "subscription_id": subscription.json()["id"]}
)

# 4. Create operator user
user = requests.post(
    f"{BASE_URL}/isp/users",
    headers=headers,
    json={
        "username": "operator1",
        "email": "op@isp.com",
        "password": "pass123",
        "role": "operator"
    }
)

# 5. Generate report
report = requests.post(
    f"{BASE_URL}/reports/generate?report_type=monthly&file_format=pdf",
    headers=headers
)

# 6. Download report
report_file = requests.get(
    f"{BASE_URL}/reports/{report.json()['report_id']}/download",
    headers=headers
)
with open("report.pdf", "wb") as f:
    f.write(report_file.content)
```

## Support

For issues or questions:
- Check the documentation: `docs/MULTI_ISP_FEATURES.md`
- Review test cases: `backend/tests/test_multi_isp_support.py`
- Open an issue on GitHub

## Next Steps

1. Complete PayPal integration
2. Complete bKash integration
3. Add automated subscription renewal
4. Implement email notifications for payments
5. Add usage tracking and analytics
6. Create admin dashboard UI
