from .dynamodb import dynamodb

def create_table(table_name):
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST"
    )
    table.wait_until_exists()

def delete_table(table_name):
    table = dynamodb.Table(table_name)
    table.delete()
