from .dynamodb import dynamodb

def put_item(table_name, item):
    table = dynamodb.Table(table_name)
    table.put_item(Item=item)

def scan_items(table_name):
    table = dynamodb.Table(table_name)
    response = table.scan()
    return response["Items"]

def delete_item(table_name, key):
    table = dynamodb.Table(table_name)
    table.delete_item(Key=key)

