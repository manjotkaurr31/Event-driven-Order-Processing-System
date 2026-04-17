# Event-Driven Order Processing System (Production-Oriented Version)

This project demonstrates a production-style, event-driven order processing system built using Azure cloud services. It simulates how modern distributed systems handle high concurrency, failures, and asynchronous workflows. The system processes customer orders using a decoupled architecture with message queues, background workers, and state persistence. This project demonstrates how distributed systems handle: Concurrency, Failures, Event-driven workflows, Observability

---

## Architecture
```
Client → API (Azure Functions) → Redis (Inventory Reservation) → Service Bus → Worker → Cosmos DB → Application Insights
```
---

## Key Features

**1. Asynchronous Processing (Azure Service Bus)**
- Orders are not processed immediately
- API pushes messages to Azure Service Bus
- Background worker processes them independently

**2. Inventory Reservation using **Redis****
- Redis is used as an in-memory cache for stock management
- Atomic operations (DECR, INCR) prevent race conditions
- Ensures no overselling during high concurrency

**3. Retry Mechanism**
- Service Bus automatically retries failed messages
- Delivery count is tracked
- Orders are marked as FAILED after max retries

**4. Compensation Logic**
- If processing fails, reserved stock is restored in Redis
- Prevents inventory inconsistency

**5. Persistent Storage (Cosmos DB)**
- Stores order states: CREATED, PROCESSING, COMPLETED, FAILED
- Enables querying order status via API

**6. Observability (Azure Application Insights)**
- Structured logging for:
- Order creation
- Processing lifecycle
- Failures
- Compensation events
- Enables real-time debugging and monitoring

---

## Tech Stack

- Azure Functions (Python) - Serverless compute
- Azure Service Bus - Messaging queue
- Azure Cache for Redis - Inventory management
- Azure Cosmos DB - NoSQL database
- Azure Application Insights - Monitoring & logging
- Postman - API Testing

---

## API Endpoints

### Create Order: POST /api/createOrder
Example: https://order-system-func-mk31.azurewebsites.net/api/createOrder

**Request**
```json
{
  "item": "item_name"
}
```
**Response**
```json
{
  "orderId": "...",
  "status": "CREATED"
}
```

### Get Order Status: GET /api/getOrder/{orderID}
Example: https://order-system-func-mk31.azurewebsites.net/api/getOrder/2bb9c503-fe22-4fb5-96ff-4e5d0b67b627
Returns the latest order state from Cosmos DB.

---

## Development & Deployment

Azurite used for local storage emulation
Environment variables stored in `local.settings.json`
Deployed on Azure Functions: Click [here](https://order-system-func-mk31.azurewebsites.net) for deployed link.

---

## Version Evolution

**V1 (Basic)**
- main branch
- Azure Queue Storage
- Simple async processing

**V2 (Current)**
- redis-servicebus branch
- Service Bus integration
- Redis-based inventory reservation
- Compensation logic
- Application Insights logging

---
