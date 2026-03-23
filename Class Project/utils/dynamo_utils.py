import boto3

def get_dynamodb_table(table_name, region):
    dynamodb = boto3.resource("dynamodb", region_name=region)
    return dynamodb.Table(table_name)


def put_item(table, item):
    try:
        table.put_item(Item=item)
        print(f"[INFO] Item {item.get('puzzle_id', 'N/A')} written to DynamoDB")
    except Exception as e:
        print(f"[ERROR] Failed to write item to DynamoDB: {e}")
        raise


def get_item(table, key):
    try:
        response = table.get_item(Key=key)
        return response.get("Item")
    except Exception as e:
        print(f"[ERROR] Failed to read item from DynamoDB: {e}")
        raise


def update_item(table, key, update_expression, expression_values):
    try:
        table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        print(f"[INFO] Updated item {key} in DynamoDB")
    except Exception as e:
        print(f"[ERROR] Failed to update item in DynamoDB: {e}")
        raise