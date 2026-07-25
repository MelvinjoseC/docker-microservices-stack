import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Order Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OrderItem(BaseModel):
    product_id: str
    quantity: int
    price: float

class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItem]

class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: str

# Mock database
orders = [
    {"id": 1, "user_id": 1, "total_amount": 1389.98, "status": "PENDING"},
    {"id": 2, "user_id": 2, "total_amount": 89.99, "status": "COMPLETED"}
]

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "order-service"}

@app.get("/api/orders", response_model=List[OrderResponse])
def get_orders():
    return orders

@app.post("/api/orders", response_model=OrderResponse, status_code=210)
def create_order(order: OrderCreate):
    total = sum(item.price * item.quantity for item in order.items)
    new_order = {
        "id": len(orders) + 1,
        "user_id": order.user_id,
        "total_amount": total,
        "status": "PENDING"
    }
    orders.append(new_order)
    return new_order

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
