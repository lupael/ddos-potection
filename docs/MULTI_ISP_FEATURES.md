# Multi-ISP Support Features

This document describes the Multi-ISP support features implemented in the DDoS Protection Platform.

## Features Overview

### 1. Multi-Tenant Architecture
- **Isolated Dashboards**: Each ISP has their own isolated dashboard with their data
- **Separate Rule Sets**: Rules, alerts, and traffic logs are isolated per ISP
- **API Key Authentication**: Each ISP has a unique API key for router integration
- **Data Isolation**: All database queries are filtered by ISP ID to ensure data separation

### 2. Role-Based Access Control (RBAC)

#### Roles
- **Admin**: Full access to all features, can manage users, subscriptions, and settings
- **Operator**: Can create and modify rules, view alerts, and generate reports
- **Viewer**: Read-only access to dashboards and reports

#### Implementation
The system uses JWT-based authentication with role checks on every endpoint. Fine-grained permission dependencies are available in `backend/utils/permissions.py`:

```python
from fastapi import Depends
from utils.permissions import admin_only, admin_or_operator

# Using dependency injection (recommended)
@router.get("/admin-endpoint")
async def admin_endpoint(current_user: User = Depends(admin_only)):
    ...

@router.get("/operator-or-admin-endpoint")
async def operator_or_admin_endpoint(current_user: User = Depends(admin_or_operator)):
    ...
```

### 3. Subscription Management

#### Available Plans
- **Basic** ($29.99/month): Up to 1 Gbps protection, basic dashboard, email alerts
- **Professional** ($99.99/month): Up to 10 Gbps protection, advanced analytics, 24/7 support, SMS alerts
- **Enterprise** ($299.99/month): Unlimited protection, custom rules, dedicated support, all integrations

#### API Endpoints
```
GET  /api/v1/subscriptions/plans          # List available plans
GET  /api/v1/subscriptions/current        # Get current subscription
POST /api/v1/subscriptions/subscribe      # Create new subscription
PUT  /api/v1/subscriptions/upgrade        # Upgrade/downgrade plan
POST /api/v1/subscriptions/cancel         # Cancel subscription
GET  /api/v1/subscriptions/history        # View subscription history
PUT  /api/v1/subscriptions/auto-renew     # Update auto-renewal settings
```

### 4. Payment Integration

#### Supported Payment Gateways
1. **Stripe** (Fully implemented)
2. **PayPal** (Placeholder - needs SDK integration)
3. **bKash** (Placeholder - needs API integration)

#### Payment Endpoints
```
GET  /api/v1/payments/history                    # Payment history
GET  /api/v1/payments/{payment_id}               # Get payment details
POST /api/v1/payments/stripe/create-payment-intent  # Create Stripe payment
POST /api/v1/payments/stripe/webhook             # Stripe webhook handler
POST /api/v1/payments/paypal/create-order        # Create PayPal order
POST /api/v1/payments/bkash/create-payment       # Create bKash payment
POST /api/v1/payments/{payment_id}/confirm       # Manually confirm payment
GET  /api/v1/payments/invoices                   # List invoices
POST /api/v1/payments/invoices/generate          # Generate invoice
```

#### Stripe Integration

1. Set environment variables:
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

2. Create payment intent:
```bash
curl -X POST http://localhost:8000/api/v1/payments/stripe/create-payment-intent \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 29.99, "subscription_id": 1}'
```

3. Set up webhook in Stripe dashboard pointing to:
```
https://your-domain.com/api/v1/payments/stripe/webhook
```

### 5. Monthly Reports

#### Report Types
- **Monthly**: Last 30 days of data
- **Weekly**: Last 7 days of data
- **Daily**: Last 24 hours of data

#### Report Formats
- **PDF**: Professional formatted report with charts and recommendations
- **CSV**: Detailed alert data in spreadsheet format
- **TXT**: Simple text-based report

#### Report Contents
- Total alerts and breakdown by severity
- Critical and high severity alerts count
- Traffic statistics (packets, bytes)
- Mitigation actions taken
- Alert breakdown by type
- Recommendations based on traffic patterns

#### API Endpoints
```
GET  /api/v1/reports/                              # List all reports
POST /api/v1/reports/generate?report_type=monthly&file_format=pdf  # Generate report
GET  /api/v1/reports/{report_id}/download          # Download report
```

#### Usage Example
```python
# Generate PDF report
response = requests.post(
    "http://localhost:8000/api/v1/reports/generate",
    params={"report_type": "monthly", "file_format": "pdf"},
    headers={"Authorization": f"Bearer {token}"}
)

# Download report
report_id = response.json()["report_id"]
report = requests.get(
    f"http://localhost:8000/api/v1/reports/{report_id}/download",
    headers={"Authorization": f"Bearer {token}"}
)
```

### 6. User Management

Admins can manage users within their ISP:

#### Endpoints
```
GET    /api/v1/isp/users          # List all users
POST   /api/v1/isp/users          # Create new user
PUT    /api/v1/isp/users/{id}     # Update user
DELETE /api/v1/isp/users/{id}     # Delete user
```

#### Create User Example
```bash
curl -X POST http://localhost:8000/api/v1/isp/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "email": "operator@example.com",
    "password": "secure_password",
    "role": "operator"
  }'
```

### 7. ISP Dashboard

Get comprehensive dashboard statistics:

```
GET /api/v1/isp/dashboard-stats
```

Returns:
- ISP information (name, plan, status)
- User count
- Rule count
- Active alerts count
- Recent alerts

## Database Models

### New Models Added

#### Subscription
```python
- id: int (primary key)
- isp_id: int (foreign key)
- plan_name: str (basic/professional/enterprise)
- plan_price: Decimal
- billing_cycle: str (monthly/yearly)
- status: str (active/cancelled/expired/suspended)
- start_date: datetime
- end_date: datetime
- auto_renew: bool
```

#### Payment
```python
- id: int (primary key)
- isp_id: int (foreign key)
- subscription_id: int (foreign key, optional)
- amount: Decimal
- currency: str (USD/BDT)
- payment_method: str (stripe/paypal/bkash)
- payment_gateway_id: str
- status: str (pending/completed/failed/refunded)
- metadata: JSON
- created_at: datetime
- completed_at: datetime
```

#### Invoice
```python
- id: int (primary key)
- isp_id: int (foreign key)
- payment_id: int (foreign key, optional)
- invoice_number: str (unique)
- amount: Decimal
- currency: str
- status: str (unpaid/paid/overdue/cancelled)
- due_date: datetime
- paid_date: datetime
- file_path: str
```

### Updated Models

#### ISP
Added fields:
- `stripe_customer_id`: str (nullable)
- `paypal_customer_id`: str (nullable)

#### Report
Added field:
- `file_format`: str (pdf/csv/txt)

## Security Considerations

1. **JWT Tokens**: All API endpoints require valid JWT tokens
2. **Role Validation**: Each endpoint validates user roles before processing
3. **ISP Isolation**: All queries are filtered by ISP ID to prevent data leakage
4. **Password Hashing**: Bcrypt is used for password hashing
5. **Webhook Verification**: Stripe webhooks are verified using signatures
6. **API Key Security**: API keys are generated using secure random tokens

## Configuration

Add these environment variables:

```bash
# Payment Gateways
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
PAYPAL_CLIENT_ID=your_client_id
PAYPAL_CLIENT_SECRET=your_client_secret
BKASH_APP_KEY=your_app_key
BKASH_APP_SECRET=your_app_secret

# Report Storage
REPORTS_DIR=/app/reports  # Use persistent volume in production
```

## Deployment Notes

1. **Database Migration**: Run migrations to create new tables
2. **Persistent Storage**: Mount a persistent volume for reports at `/app/reports`
3. **Webhook Configuration**: Configure webhooks in payment gateway dashboards
4. **SSL/TLS**: Use HTTPS for all payment-related endpoints
5. **Backup**: Regular backups of payment and subscription data

## Testing

Example test flow:

1. Register new ISP
2. Login as admin
3. Create subscription
4. Add users with different roles
5. Generate report
6. Create payment
7. Download invoice

## Future Enhancements

- Automated subscription renewal
- Payment retry logic for failed payments
- Usage-based billing
- Custom report scheduling
- Email delivery of reports
- Payment method management
- Refund processing
- Discount codes and promotions
