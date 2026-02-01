from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import stripe
import os

from database import get_db
from models.models import ISP, User, Payment, Invoice, Subscription
from routers.auth_router import get_current_user

router = APIRouter()

# Initialize Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

class PaymentCreate(BaseModel):
    amount: Decimal
    payment_method: str  # stripe, paypal, bkash
    subscription_id: Optional[int] = None
    description: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    description: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class StripePaymentIntent(BaseModel):
    subscription_id: Optional[int] = None
    amount: Decimal

class PayPalOrder(BaseModel):
    subscription_id: Optional[int] = None
    amount: Decimal

class BkashPayment(BaseModel):
    subscription_id: Optional[int] = None
    amount: Decimal
    phone_number: str

@router.get("/history", response_model=List[PaymentResponse])
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment history for the ISP"""
    payments = db.query(Payment).filter(
        Payment.isp_id == current_user.isp_id
    ).order_by(Payment.created_at.desc()).all()
    
    return payments

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific payment"""
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.isp_id == current_user.isp_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return payment

@router.post("/stripe/create-payment-intent")
async def create_stripe_payment_intent(
    payment_data: StripePaymentIntent,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe payment intent (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get or create Stripe customer
        isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
        
        if not isp.stripe_customer_id:
            customer = stripe.Customer.create(
                email=isp.email,
                name=isp.name,
                metadata={"isp_id": str(isp.id)}
            )
            isp.stripe_customer_id = customer.id
            db.commit()
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(payment_data.amount * 100),  # Convert to cents
            currency="usd",
            customer=isp.stripe_customer_id,
            metadata={
                "isp_id": str(current_user.isp_id),
                "subscription_id": str(payment_data.subscription_id) if payment_data.subscription_id else None
            }
        )
        
        # Create payment record
        payment = Payment(
            isp_id=current_user.isp_id,
            subscription_id=payment_data.subscription_id,
            amount=payment_data.amount,
            currency="USD",
            payment_method="stripe",
            payment_gateway_id=intent.id,
            status="pending",
            metadata={"stripe_payment_intent_id": intent.id}
        )
        db.add(payment)
        db.commit()
        
        return {
            "client_secret": intent.client_secret,
            "payment_id": payment.id,
            "payment_intent_id": intent.id
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        
        # Update payment record
        payment = db.query(Payment).filter(
            Payment.payment_gateway_id == payment_intent.id
        ).first()
        
        if payment:
            payment.status = "completed"
            payment.completed_at = datetime.utcnow()
            db.commit()
    
    elif event.type == "payment_intent.payment_failed":
        payment_intent = event.data.object
        
        # Update payment record
        payment = db.query(Payment).filter(
            Payment.payment_gateway_id == payment_intent.id
        ).first()
        
        if payment:
            payment.status = "failed"
            db.commit()
    
    return {"status": "success"}

@router.post("/paypal/create-order")
async def create_paypal_order(
    payment_data: PayPalOrder,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a PayPal order (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Note: This is a simplified version. In production, you would integrate with PayPal SDK
    # and create an actual order using PayPal API
    
    import uuid
    
    payment = Payment(
        isp_id=current_user.isp_id,
        subscription_id=payment_data.subscription_id,
        amount=payment_data.amount,
        currency="USD",
        payment_method="paypal",
        payment_gateway_id=f"PAYPAL-PLACEHOLDER-{uuid.uuid4()}",
        status="pending",
        metadata={"note": "PayPal integration - implement with PayPal SDK"}
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return {
        "payment_id": payment.id,
        "order_id": payment.payment_gateway_id,
        "message": "PayPal order created - integrate with PayPal SDK for actual processing"
    }

@router.post("/bkash/create-payment")
async def create_bkash_payment(
    payment_data: BkashPayment,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a bKash payment (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Note: This is a simplified version. In production, you would integrate with bKash API
    # bKash requires authentication and specific API calls
    
    import uuid
    
    payment = Payment(
        isp_id=current_user.isp_id,
        subscription_id=payment_data.subscription_id,
        amount=payment_data.amount,
        currency="BDT",  # bKash uses Bangladeshi Taka
        payment_method="bkash",
        payment_gateway_id=f"BKASH-PLACEHOLDER-{uuid.uuid4()}",
        status="pending",
        metadata={
            "phone_number": payment_data.phone_number,
            "note": "bKash integration - implement with bKash API"
        }
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return {
        "payment_id": payment.id,
        "transaction_id": payment.payment_gateway_id,
        "message": "bKash payment created - integrate with bKash API for actual processing"
    }

@router.post("/{payment_id}/confirm")
async def confirm_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually confirm a payment (admin only) - for manual payment methods"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.isp_id == current_user.isp_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.status == "completed":
        raise HTTPException(status_code=400, detail="Payment already completed")
    
    payment.status = "completed"
    payment.completed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Payment confirmed successfully"}

@router.get("/invoices", response_model=List)
async def get_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all invoices for the ISP"""
    invoices = db.query(Invoice).filter(
        Invoice.isp_id == current_user.isp_id
    ).order_by(Invoice.created_at.desc()).all()
    
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "amount": str(inv.amount),
            "currency": inv.currency,
            "status": inv.status,
            "due_date": inv.due_date,
            "paid_date": inv.paid_date,
            "created_at": inv.created_at
        }
        for inv in invoices
    ]

@router.post("/invoices/generate")
async def generate_invoice(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate an invoice for a subscription (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.isp_id == current_user.isp_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Generate invoice number
    invoice_number = f"INV-{current_user.isp_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Create invoice
    invoice = Invoice(
        isp_id=current_user.isp_id,
        invoice_number=invoice_number,
        amount=subscription.plan_price,
        currency="USD",
        status="unpaid",
        due_date=datetime.utcnow() + timedelta(days=30)
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "amount": str(invoice.amount),
        "due_date": invoice.due_date
    }
