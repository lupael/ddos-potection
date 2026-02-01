"""
Database migration script for Multi-ISP Support features

This script adds new tables for subscriptions, payments, and invoices,
and updates existing tables with new fields.

Run this script after updating models.py to create the new tables.
"""

from sqlalchemy import create_engine, text
import os

# Get database URL from environment
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ddos_user:ddos_pass@localhost:5432/ddos_platform"
)

def run_migration():
    """Run database migration for Multi-ISP Support"""
    
    engine = create_engine(DATABASE_URL)
    
    print("Running Multi-ISP Support migration...")
    
    # SQL statements for migration
    migrations = [
        # Add new fields to ISP table
        """
        ALTER TABLE isps 
        ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS paypal_customer_id VARCHAR(255);
        """,
        
        # Add file_format to reports table
        """
        ALTER TABLE reports 
        ADD COLUMN IF NOT EXISTS file_format VARCHAR(10) DEFAULT 'txt';
        """,
        
        # Create subscriptions table
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            isp_id INTEGER NOT NULL REFERENCES isps(id) ON DELETE CASCADE,
            plan_name VARCHAR(50) NOT NULL,
            plan_price NUMERIC(10, 2) NOT NULL,
            billing_cycle VARCHAR(20) DEFAULT 'monthly',
            status VARCHAR(50) DEFAULT 'active',
            start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            end_date TIMESTAMP WITH TIME ZONE,
            auto_renew BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        );
        """,
        
        # Create indexes for subscriptions
        """
        CREATE INDEX IF NOT EXISTS idx_subscriptions_isp_id ON subscriptions(isp_id);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
        """,
        
        # Create payments table
        """
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            isp_id INTEGER NOT NULL REFERENCES isps(id) ON DELETE CASCADE,
            subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
            amount NUMERIC(10, 2) NOT NULL,
            currency VARCHAR(10) DEFAULT 'USD',
            payment_method VARCHAR(50) NOT NULL,
            payment_gateway_id VARCHAR(255),
            status VARCHAR(50) DEFAULT 'pending',
            description TEXT,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        );
        """,
        
        # Create indexes for payments
        """
        CREATE INDEX IF NOT EXISTS idx_payments_isp_id ON payments(isp_id);
        CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
        CREATE INDEX IF NOT EXISTS idx_payments_gateway_id ON payments(payment_gateway_id);
        """,
        
        # Create invoices table
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            isp_id INTEGER NOT NULL REFERENCES isps(id) ON DELETE CASCADE,
            payment_id INTEGER REFERENCES payments(id) ON DELETE SET NULL,
            invoice_number VARCHAR(100) UNIQUE NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            currency VARCHAR(10) DEFAULT 'USD',
            status VARCHAR(50) DEFAULT 'unpaid',
            due_date TIMESTAMP WITH TIME ZONE NOT NULL,
            paid_date TIMESTAMP WITH TIME ZONE,
            file_path VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Create indexes for invoices
        """
        CREATE INDEX IF NOT EXISTS idx_invoices_isp_id ON invoices(isp_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
        CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number);
        """
    ]
    
    # Execute migrations
    with engine.connect() as conn:
        for i, migration_sql in enumerate(migrations, 1):
            try:
                print(f"Running migration {i}/{len(migrations)}...")
                conn.execute(text(migration_sql))
                conn.commit()
                print(f"✓ Migration {i} completed successfully")
            except Exception as e:
                print(f"✗ Migration {i} failed: {str(e)}")
                # Continue with other migrations
                conn.rollback()
    
    print("\nMigration completed!")
    print("\nNew tables created:")
    print("- subscriptions")
    print("- payments")
    print("- invoices")
    print("\nUpdated tables:")
    print("- isps (added stripe_customer_id, paypal_customer_id)")
    print("- reports (added file_format)")

def rollback_migration():
    """Rollback the migration (optional)"""
    
    engine = create_engine(DATABASE_URL)
    
    print("Rolling back Multi-ISP Support migration...")
    
    rollback_sql = [
        "DROP TABLE IF EXISTS invoices CASCADE;",
        "DROP TABLE IF EXISTS payments CASCADE;",
        "DROP TABLE IF EXISTS subscriptions CASCADE;",
        "ALTER TABLE isps DROP COLUMN IF EXISTS stripe_customer_id, DROP COLUMN IF EXISTS paypal_customer_id;",
        "ALTER TABLE reports DROP COLUMN IF EXISTS file_format;"
    ]
    
    with engine.connect() as conn:
        for sql in rollback_sql:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"✓ Rollback step completed")
            except Exception as e:
                print(f"✗ Rollback failed: {str(e)}")
                conn.rollback()
    
    print("Rollback completed!")

def verify_migration():
    """Verify that migration was successful"""
    
    engine = create_engine(DATABASE_URL)
    
    print("\nVerifying migration...")
    
    check_tables = [
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'subscriptions';",
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'payments';",
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'invoices';",
    ]
    
    with engine.connect() as conn:
        for sql in check_tables:
            result = conn.execute(text(sql))
            count = result.scalar()
            table_name = sql.split("'")[1]
            if count > 0:
                print(f"✓ Table '{table_name}' exists")
            else:
                print(f"✗ Table '{table_name}' does not exist")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        confirm = input("Are you sure you want to rollback the migration? (yes/no): ")
        if confirm.lower() == "yes":
            rollback_migration()
        else:
            print("Rollback cancelled")
    elif len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_migration()
    else:
        run_migration()
        verify_migration()
