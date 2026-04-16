import azure.functions as func
import datetime
import json
import logging
import time
import random
from azure.cosmos import CosmosClient
import os

app =func.FunctionApp()
import uuid

@app.route(route="createOrder", auth_level=func.AuthLevel.ANONYMOUS)
@app.queue_output(arg_name="msg",queue_name="orders",connection="AzureWebJobsStorage")
def createOrder(req: func.HttpRequest, msg: func.Out[str]) -> func.HttpResponse:
    try:
        data=req.get_json()
        order={ "id": str(uuid.uuid4()), "orderId":str(uuid.uuid4()), "item": data.get("item"),  "status": "CREATED"}
        msg.set(json.dumps(order))
        logging.info(f"Order pushed to queue: {order}")
        return func.HttpResponse(json.dumps(order),status_code=200,mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(str(e), status_code=400)
    

@app.queue_trigger(arg_name="azqueue", queue_name="orders",connection="AzureWebJobsStorage") 
def processOrder(azqueue: func.QueueMessage):
    order=json.loads(azqueue.get_body().decode('utf-8'))
    COSMOS_URI=os.environ.get("COSMOS_URI")
    COSMOS_KEY=os.environ.get("COSMOS_KEY")
    client=CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
    database=client.get_database_client("orders-db")
    container= database.get_container_client("orders")
    logging.info(f"[{order['orderId']}] Received for processing | Attempt: {azqueue.dequeue_count}")
    if azqueue.dequeue_count >3:
        order["status"]="FAILED"
        container.upsert_item(order)
        logging.error(f"[{order['orderId']}] Marked FAILED after max retries")
        return
    order["status"]= "PROCESSING"
    container.upsert_item(order)
    time.sleep(2)
    if random.random()<0.3:
        logging.error(f"[{order['orderId']}] Simulated failure")
        raise Exception("Payment failed")
    order["status"]= "COMPLETED"
    container.upsert_item(order)
    logging.info(f"[{order['orderId']}] Completed successfully")


@app.route(route="getOrder/{id}", auth_level=func.AuthLevel.ANONYMOUS)
def getOrder(req: func.HttpRequest)-> func.HttpResponse:
    try:
        order_id=req.route_params.get("id")
        COSMOS_URI=os.environ.get("COSMOS_URI")
        COSMOS_KEY= os.environ.get("COSMOS_KEY")
        client= CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
        database=client.get_database_client("orders-db")
        container= database.get_container_client("orders")
        query= "SELECT * FROM c WHERE c.orderId=@orderId"
        parameters=[{"name": "@orderId", "value": order_id}]
        items=list(container.query_items(query=query,parameters=parameters,enable_cross_partition_query=True))
        if not items:
            return func.HttpResponse("Order not found", status_code=404)
        return func.HttpResponse(json.dumps(items[0]),status_code=200, mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)
