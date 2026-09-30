import os
import time
import json
import pika
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, Float, String, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from prometheus_client import make_asgi_app

app = FastAPI(title="Order Service", version="1.0.0")

# Mount Prometheus ASGI metrics app
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
import json
import datetime
import uuid

@app.middleware("http")
async def log_requests(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id") or f"order-{uuid.uuid4()}"
    start_time = datetime.datetime.utcnow()
    
    response = await call_next(request)
    duration = (datetime.datetime.utcnow() - start_time).total_seconds() * 1000
    
    response.headers["X-Correlation-ID"] = correlation_id
    
    if request.url.path != "/metrics":
        log_data = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "level": "error" if response.status_code >= 400 else "info",
            "message": f"{request.method} {request.url.path} - {response.status_code}",
            "service": "order-service",
            "duration_ms": round(duration, 2)
        }
        print(json.dumps(log_data), flush=True)
        
    return response

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://devuser:devpassword@postgres:5432/microservices_db"
)

is_testing = os.getenv("TESTING") == "1"
if is_testing:
    DATABASE_URL = "sqlite:///:memory:"

engine = None
retries = 1 if is_testing else 5
delay = 0 if is_testing else 3

for i in range(retries):
    try:
        print(f"Connecting to database (attempt {i+1}/{retries})...")
        connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
        engine = create_engine(DATABASE_URL, connect_args=connect_args)
        with engine.connect() as conn:
            print("Successfully connected to database")
            break
    except Exception as e:
        print(f"Database connection error: {e}, retrying in {delay}s...")
        if i < retries - 1:
            time.sleep(delay)

if not engine:
    print("Warning: Database connection failed. Falling back to in-memory SQLite.")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Models
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String, default="PENDING")
    items = Column(JSON, nullable=False)  # Store items list as JSON

# Create database tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from pydantic import BaseModel, Field

# Pydantic Schemas
class OrderItemSchema(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, description="Quantity must be at least 1")
    price: float = Field(gt=0.0, description="Price must be greater than 0")

class OrderCreateSchema(BaseModel):
    user_id: int = Field(gt=0, description="User ID must be positive")
    items: List[OrderItemSchema] = Field(min_length=1, description="Order must contain at least one item")

class OrderResponseSchema(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: str
    items: List[OrderItemSchema]

    class Config:
        from_attributes = True

# Seed database if empty
db = SessionLocal()
if db.query(Order).count() == 0:
    mock_orders = [
        Order(
            id=1, 
            user_id=1, 
            total_amount=1389.98, 
            status="PENDING", 
            items=[{"product_id": "p1", "quantity": 1, "price": 1299.99}, {"product_id": "p2", "quantity": 1, "price": 89.99}]
        ),
        Order(
            id=2, 
            user_id=2, 
            total_amount=89.99, 
            status="COMPLETED", 
            items=[{"product_id": "p2", "quantity": 1, "price": 89.99}]
        )
    ]
    db.add_all(mock_orders)
    db.commit()
    print("Database seeded with default orders.")
db.close()

class RabbitMQPublisher:
    def __init__(self, host=None):
        self.host = host or os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.connection = None
        self.channel = None

    def get_channel(self):
        try:
            if self.connection and self.connection.is_open and self.channel and self.channel.is_open:
                return self.channel
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.host, connection_attempts=3, retry_delay=2)
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue='order_notifications', durable=True)
            return self.channel
        except Exception as e:
            print(f"RabbitMQ connection failed: {e}", flush=True)
            return None

    def publish_order_notification(self, message_dict):
        channel = self.get_channel()
        if not channel:
            print("Warning: Skipping message publication, RabbitMQ unavailable", flush=True)
            return False
        try:
            channel.basic_publish(
                exchange='',
                routing_key='order_notifications',
                body=json.dumps(message_dict),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            print(" [x] Sent order notification event to RabbitMQ", flush=True)
            return True
        except Exception as err:
            print(f"Error publishing message: {err}", flush=True)
            self.connection = None
            return False

publisher = RabbitMQPublisher()

class OrderStatusUpdateSchema(BaseModel):
    status: str

@app.get("/health")
@app.get("/api/orders/health")
def health_check(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "service": "order-service"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "service": "order-service"}

@app.get("/api/orders", response_model=List[OrderResponseSchema])
def get_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.id.asc()).all()

@app.get("/api/orders/{order_id}", response_model=OrderResponseSchema)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.post("/api/orders", response_model=OrderResponseSchema, status_code=201)
def create_order(order: OrderCreateSchema, db: Session = Depends(get_db)):
    total = sum(item.price * item.quantity for item in order.items)
    
    items_list = [item.model_dump() if hasattr(item, 'model_dump') else item.dict() for item in order.items]
    
    db_order = Order(
        user_id=order.user_id,
        total_amount=total,
        status="PENDING",
        items=items_list
    )
    
    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        
        # Publish async notification event to RabbitMQ broker
        notification_payload = {
            "id": db_order.id,
            "user_id": db_order.user_id,
            "total_amount": db_order.total_amount,
            "items": items_list
        }
        publisher.publish_order_notification(notification_payload)

        return db_order
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/orders/{order_id}/status", response_model=OrderResponseSchema)
def update_order_status(order_id: int, update: OrderStatusUpdateSchema, db: Session = Depends(get_db)):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    db_order.status = update.status.upper()
    db.commit()
    db.refresh(db_order)
    return db_order

@app.delete("/api/orders/{order_id}", status_code=200)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(db_order)
    db.commit()
    return {"message": f"Order #{order_id} successfully deleted"}
