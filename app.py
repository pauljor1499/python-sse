from fastapi import FastAPI, HTTPException, status, Query
from models import Product, ProductUpdate
from product_service import ProductService
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio

app = FastAPI()

# Initialize ProductService with MongoDB URI
db_url = "mongodb+srv://admin:admin@cluster0.aeltnpt.mongodb.net/"
product_service = ProductService(db_url)

# Store connected clients for SSE
clients = []

@app.post("/products/")
async def create_product(product: Product):
    product_data = product.model_dump()
    product_id = await product_service.create_product(product_data)
    await notify_clients(f"New product added: {product_id}")
    return {"id": product_id}

@app.get("/products/{product_id}")
async def read_product(product_id: str):
    product = await product_service.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}")
async def update_product(product_id: str, product_update: ProductUpdate):
    updated_data = {k: v for k, v in product_update.model_dump().items() if v is not None}
    if not await product_service.get_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    await product_service.update_product(product_id, updated_data)
    await notify_clients(f"Product updated: {product_id}")
    return {"msg": "Product updated"}

@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    if not await product_service.delete_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    await notify_clients(f"Product deleted: {product_id}")
    return {"msg": "Product deleted"}

@app.get("/products/")
async def list_products():
    products = await product_service.list_products()
    return products


# SSE route to stream events to clients
@app.get("/events/")
async def events():
    async def event_stream():
        queue = asyncio.Queue()  # Create a queue for each client
        clients.append(queue)
        try:
            while True:
                data = await queue.get()  # Wait for messages to send to client
                yield data
        except asyncio.CancelledError:
            clients.remove(queue)  # Remove client on disconnect
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Notify all connected clients
async def notify_clients(message: str):
    if clients:
        for client in clients:
            await client.put(f"data: {message}\n\n")
