import azure.functions as func
import json
import logging
import time
import random
from azure.cosmos import CosmosClient
import os
import uuid
import redis

app = func.FunctionApp()




redis_client = redis.Redis.from_url(os.environ.get("REDIS_CONNECTION"))







@app.route(route="createOrder", auth_level=func.AuthLevel.ANONYMOUS)
@app.service_bus_queue_output( arg_name="msg", queue_name="orders",connection="ServiceBusConnection")
def createOrder(req: func.HttpRequest, msg: func.Out[str]) -> func.HttpResponse:
    try:
        data =req.get_json()
        item=data.get("item")
        if not item:
            logging.warning("[CREATE-ERROR] Missing item in request")
            return func.HttpResponse("Item is required", status_code=400)
        item = item.strip().lower()
        key = f"stock:{item}"
        logging.info(f"[CREATE-START] Item={item}")

        try:
            stock_before = redis_client.get(key)
            logging.info(f"[CREATE-STOCK] Before={stock_before} Key={key}")
            stock = redis_client.decr(key)
            logging.info(f"[CREATE-STOCK] After={stock} Key={key}")
            if stock< 0:
                redis_client.incr(key)
                logging.warning(f"[CREATE-REJECTED] Item={item} OutOfStock")
                return func.HttpResponse("Out of stock", status_code=400)
            

        except Exception as e:
            logging.error(f"[CREATE-REDIS-ERROR] Item={item} Error={str(e)}")

            return func.HttpResponse("Inventory service unavailable", status_code=500)
        
        order = {
            "id": str(uuid.uuid4()),
            "orderId": str(uuid.uuid4()),
            "item": item,
            "status": "CREATED"
        }
        msg.set(json.dumps(order))
        logging.info(f"[CREATE-SUCCESS] OrderId={order['orderId']} Item={item}")
        return func.HttpResponse(json.dumps(order),status_code=200, mimetype="application/json" )
    
    except Exception as e:
        logging.error(f"[CREATE-FAIL] Error={str(e)}")

        return func.HttpResponse(str(e), status_code=400)






@app.service_bus_queue_trigger(arg_name="msg", queue_name="orders",connection="ServiceBusConnection")
def processOrder(msg: func.ServiceBusMessage):
    order = json.loads(msg.get_body().decode('utf-8'))
    COSMOS_URI = os.environ.get("COSMOS_URI")
    COSMOS_KEY = os.environ.get("COSMOS_KEY")


    client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
    database = client.get_database_client("orders-db")
    container = database.get_container_client("orders")




    delivery_count = msg.delivery_count
    item = order.get("item")
    redis_key = f"stock:{item}"
    logging.info(f"[PROCESS-START] OrderId={order['orderId']} Attempt={delivery_count}")
    if delivery_count > 3:
        order["status"] = "FAILED"
        container.upsert_item(order)
        try:
            redis_client.incr(redis_key)
            logging.info(f"[COMPENSATION] OrderId={order['orderId']} StockRestored")


        except Exception as e:
            logging.error(f"[COMPENSATION-ERROR] OrderId={order['orderId']} Error={str(e)}")
        logging.error(f"[PROCESS-FAILED-MAX-RETRY] OrderId={order['orderId']}")

        return
    
    order["status"] = "PROCESSING"
    container.upsert_item(order)
    logging.info(f"[PROCESSING] OrderId={order['orderId']}")
    try:
        time.sleep(2)
        if random.random() < 0.3:
            raise Exception("Payment failed")
        order["status"] = "COMPLETED"
        container.upsert_item(order)
        logging.info(f"[PROCESS-SUCCESS] OrderId={order['orderId']}")


    except Exception as e:
        logging.error(f"[PROCESS-FAIL] OrderId={order['orderId']} Error={str(e)}")
        try:
            redis_client.incr(redis_key)
            logging.info(f"[COMPENSATION] OrderId={order['orderId']} StockRestored")
        except Exception as redis_err:
            logging.error(f"[COMPENSATION-ERROR] OrderId={order['orderId']} Error={str(redis_err)}")
        raise e
    






@app.route(route="getOrder/{id}", auth_level=func.AuthLevel.ANONYMOUS)
def getOrder(req: func.HttpRequest) -> func.HttpResponse:
    try:
        order_id = req.route_params.get("id")

        if not order_id:
            logging.warning("[GET-ERROR] Missing orderId in request")
            return func.HttpResponse("Order ID is required", status_code=400)

        logging.info(f"[GET-START] OrderId={order_id}")

        COSMOS_URI = os.environ.get("COSMOS_URI")
        COSMOS_KEY = os.environ.get("COSMOS_KEY")

        client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
        database = client.get_database_client("orders-db")
        container = database.get_container_client("orders")

        query = "SELECT * FROM c WHERE c.orderId=@orderId"
        parameters = [{"name": "@orderId", "value": order_id}]

        items = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        if not items:
            logging.warning(f"[GET-NOT-FOUND] OrderId={order_id}")
            return func.HttpResponse("Order not found", status_code=404)

        logging.info(f"[GET-SUCCESS] OrderId={order_id}")

        return func.HttpResponse(
            json.dumps(items[0]),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"[GET-FAIL] OrderId={order_id} Error={str(e)}")
        return func.HttpResponse(str(e), status_code=500)