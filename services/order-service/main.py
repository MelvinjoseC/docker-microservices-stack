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

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://devuser:devpassword@postgres:5432/microservices_db"
)

# Retry connection logic for PostgreSQL
engine = None
for i in range(5):
    try:
        print(f"Connecting to PostgreSQL (attempt {i+1}/5)...")
        engine = create_engine(DATABASE_URL)
        # Test connection
        with engine.connect() as conn:
            print("Successfully connected to PostgreSQL")
            break
    except Exception as e:
        print(f"PostgreSQL connection error: {e}, retrying in 5 seconds...")
        time.sleep(5)

if not engine:
    raise RuntimeError("Failed to connect to database after 5 attempts")

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

# Pydantic Schemas
class OrderItemSchema(BaseModel):
    product_id: str
    quantity: int
    price: float

class OrderCreateSchema(BaseModel):
    user_id: int
    items: List[OrderItemSchema]

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

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Simple query to check DB availability
        db.execute(Base.metadata.tables["orders"].select().limit(1))
        return {"status": "healthy", "database": "connected", "service": "order-service"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "service": "order-service"}

@app.get("/api/orders", response_model=List[OrderResponseSchema])
def get_orders(db: Session = Depends(get_db)):
    return db.query(Order).all()

@app.post("/api/orders", response_model=OrderResponseSchema, status_code=201)
def create_order(order: OrderCreateSchema, db: Session = Depends(get_db)):
    total = sum(item.price * item.quantity for item in order.items)
    
    # Convert Pydantic schemas to dict for JSON column storing
    items_list = [item.dict() for item in order.items]
    
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
        
        # Publish event to RabbitMQ
        try:
            rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
            channel = connection.channel()
            channel.queue_declare(queue='order_notifications', durable=True)
            message = {
                "id": db_order.id,
                "user_id": db_order.user_id,
                "total_amount": db_order.total_amount,
                "items": items_list
            }
            channel.basic_publish(
                exchange='',
                routing_key='order_notifications',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                )
            )
            connection.close()
            print(" [x] Sent order notification event to RabbitMQ", flush=True)
        except Exception as mq_err:
            print(f"Failed to publish RabbitMQ message: {mq_err}", flush=True)

        return db_order
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
