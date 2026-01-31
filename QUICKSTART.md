# Quick Start Guide

Get the DDoS Protection Platform running in under 10 minutes!

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available
- Ports 80, 443, 3000, 8000 available

## Step 1: Clone Repository

```bash
git clone https://github.com/i4edubd/ddos-potection.git
cd ddos-potection
```

## Step 2: Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

Expected output:
```
NAME                COMMAND                  STATUS              PORTS
ddos-backend        "uvicorn main:app..."    Up                  0.0.0.0:8000->8000/tcp
ddos-collector      "python services/..."    Up                  0.0.0.0:2055->2055/udp
ddos-detector       "python services/..."    Up                  
ddos-frontend       "npm start"              Up                  0.0.0.0:3000->3000/tcp
ddos-grafana        "/run.sh"                Up                  0.0.0.0:3001->3000/tcp
ddos-postgres       "docker-entrypoint..."   Up                  0.0.0.0:5432->5432/tcp
ddos-prometheus     "/bin/prometheus..."     Up                  0.0.0.0:9090->9090/tcp
ddos-redis          "docker-entrypoint..."   Up                  0.0.0.0:6379->6379/tcp
```

## Step 3: Access the Platform

Open your browser and navigate to:

**Dashboard**: http://localhost:3000

## Step 4: Create Your Account

Register via API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@yourisp.com",
    "password": "YourSecurePassword123!",
    "isp_name": "Your ISP Name",
    "role": "admin"
  }'
```

Then login at http://localhost:3000 with your credentials.

## Step 5: Explore the Dashboard

### Main Dashboard
- View real-time traffic statistics
- Monitor active alerts
- See attack patterns

### Configure Your First Rule

1. Click "Rules" in the navigation
2. Click "Add Rule"
3. Fill in the form:
   ```
   Name: Block malicious IP
   Type: IP Block
   Action: Block
   Priority: 100
   Condition: {"ip": "1.2.3.4"}
   ```
4. Click "Create Rule"

### Monitor Traffic

1. Click "Traffic" in the navigation
2. View protocol distribution
3. See recent traffic logs

### View Alerts

1. Click "Alerts" in the navigation
2. See active security alerts
3. Click "Mitigate" to automatically respond
4. Click "Resolve" to mark as resolved

### Generate Reports

1. Click "Reports" in the navigation
2. Click "Daily Report", "Weekly Report", or "Monthly Report"
3. View generated reports in the table
4. Click "Download" to get the report file

### Configure Settings

1. Click "Settings" in the navigation
2. View your ISP information
3. See your API key for router integration
4. Configure detection thresholds
5. Set up notification channels

## Step 6: Integrate Your Routers

### MikroTik Router

```bash
# Run the integration script
python scripts/mikrotik_integration.py \
  192.168.1.1 \
  admin \
  password \
  YOUR_SERVER_IP \
  2055
```

### Cisco Router

```bash
# Generate configuration
bash scripts/cisco_netflow.sh 192.168.1.1 YOUR_SERVER_IP 2055
```

Copy and paste the generated commands into your Cisco router.

### Juniper Router

```bash
# Generate configuration
bash scripts/juniper_sflow.sh 192.168.1.1 YOUR_SERVER_IP 6343
```

Copy and paste the generated commands into your Juniper router.

## Step 7: Monitor with Grafana

1. Open http://localhost:3001
2. Login with `admin` / `admin`
3. Change the password when prompted
4. Add Prometheus as a data source:
   - URL: `http://prometheus:9090`
5. Import dashboards from `docs/grafana/`

## Step 8: (Optional) Setup BGP Blackholing

For advanced DDoS mitigation using BGP-based traffic dropping:

1. **Check if you need BGP blackholing**:
   - Do you have a BGP session with your upstream ISP?
   - Does your ISP support RTBH (blackhole community)?
   - If yes, continue. If no, skip this section.

2. **See complete BGP setup guide**:
   ```bash
   # Read the comprehensive BGP documentation
   cat docs/BGP-RTBH.md
   ```

3. **Quick BGP Setup** (ExaBGP example):
   ```bash
   # Install ExaBGP
   pip3 install exabgp
   
   # Configure (see docs/BGP-RTBH.md for details)
   sudo cp docs/examples/exabgp.conf /etc/exabgp/
   
   # Enable in platform
   echo "BGP_ENABLED=true" >> backend/.env
   echo "BGP_DAEMON=exabgp" >> backend/.env
   
   # Restart backend
   docker-compose restart backend
   ```

4. **Test BGP blackhole**:
   ```bash
   # Use the example script
   python3 scripts/bgp_blackhole_example.py trigger \
     --ip 192.0.2.100 --alert-id 1 --duration 60
   ```

For complete BGP setup instructions, see [BGP-RTBH.md](docs/BGP-RTBH.md).

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs -f

# Restart specific service
docker-compose restart backend

# Rebuild and restart
docker-compose up -d --build
```

### Can't Access Frontend

1. Check if port 3000 is available:
   ```bash
   lsof -i :3000
   ```

2. View frontend logs:
   ```bash
   docker-compose logs frontend
   ```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis
docker exec ddos-redis redis-cli ping
```

## Next Steps

1. **Configure Notifications**: Set up email/Telegram alerts in Settings
2. **Customize Thresholds**: Adjust detection thresholds for your network
3. **Add Users**: Invite team members with different roles
4. **Review Documentation**: Read the full documentation in `docs/`
5. **Integrate Routers**: Connect your network equipment
6. **Set Up Monitoring**: Configure Grafana dashboards

## Getting Help

- **Documentation**: See `docs/` folder
- **GitHub Issues**: https://github.com/i4edubd/ddos-potection/issues
- **API Docs**: http://localhost:8000/docs

## Important Security Notes

For production deployment:

1. **Change default passwords**
2. **Use strong SECRET_KEY** in backend/.env
3. **Enable SSL/TLS** (see docs/DEPLOYMENT.md)
4. **Configure firewall** rules
5. **Set up backups** (see docs/DEPLOYMENT.md)
6. **Update ALLOWED_ORIGINS** for CORS

See `docs/DEPLOYMENT.md` for complete production setup guide.

## What's Next?

Now that you have the platform running, you can:

- Monitor incoming traffic from your routers
- Detect and respond to DDoS attacks automatically
- Generate compliance reports for your ISP
- Scale to multiple ISP customers (multi-tenant)
- Integrate payment processing for paid services

Happy DDoS hunting! 🛡️
