import json
import os
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
s3 = boto3.resource("s3")

# DYNAMODB OPERATIONS
def create_dynamo_table(table_name, partition_key="item_id"):
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": partition_key, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": partition_key, "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
        )
        table.wait_until_exists()
        print(f"Created DynamoDB table: {table_name}")
    except ClientError as e:
        print(f"Error creating table {table_name}: {e}")

def delete_dynamo_table(table_name):
    try:
        table = dynamodb.Table(table_name)
        table.delete()
        print(f"Deleted DynamoDB table: {table_name}")
    except ClientError as e:
        print(f"Error deleting table {table_name}: {e}")

def empty_dynamo_table(table_name):
    try:
        table = dynamodb.Table(table_name)
        response = table.scan()
        items = response.get("Items", [])
        if not items:
            print(f"DynamoDB table {table_name} is already empty")
            return
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"item_id": item["item_id"]})
        print(f"Emptied DynamoDB table: {table_name}")
    except ClientError as e:
        print(f"Error emptying table {table_name}: {e}")

def populate_dynamo_table(table_name, data_file):
    try:
        table = dynamodb.Table(table_name)
        with open(data_file, "r") as f:
            items = json.load(f)
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
        print(f"Populated DynamoDB table: {table_name}")
    except Exception as e:
        print(f"Error populating table {table_name}: {e}")

# S3 OPERATIONS
def create_s3_bucket(bucket_name, region="us-east-1"):
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region}
            )
        print(f"Created S3 bucket: {bucket_name}")
    except ClientError as e:
        print(f"Error creating bucket {bucket_name}: {e}")

def delete_s3_bucket(bucket_name):
    try:
        bucket = s3.Bucket(bucket_name)
        bucket.delete()
        print(f"Deleted S3 bucket: {bucket_name}")
    except ClientError as e:
        print(f"Error deleting bucket {bucket_name}: {e}")

def empty_s3_bucket(bucket_name):
    try:
        bucket = s3.Bucket(bucket_name)
        bucket.objects.all().delete()
        print(f"Emptied S3 bucket: {bucket_name}")
    except ClientError as e:
        print(f"Error emptying bucket {bucket_name}: {e}")

def populate_s3_bucket(bucket_name, folder_path):
    try:
        bucket = s3.Bucket(bucket_name)
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                bucket.upload_file(file_path, file_name)
        print(f"Populated S3 bucket: {bucket_name}")
    except Exception as e:
        print(f"Error populating bucket {bucket_name}: {e}")

# MAIN SCRIPT
# Will skip task that are empty on required fields.
def main():
    with open("tasks.json") as f:
        tasks = json.load(f)["tasks"]

    for task in tasks:
        task_name = task.get("name", "")
        if not task_name:
            print("Skipping task with no name")
            continue

        # Check for required fields before running each task
        if task_name == "create_dynamo_db_table":
            table_name = task.get("table")
            if table_name:
                create_dynamo_table(table_name, task.get("partition_key", "item_id"))
            else:
                print("Skipping create_dynamo_db_table: no table name specified")

        elif task_name == "delete_dynamo_db_table":
            table_name = task.get("table")
            if table_name:
                delete_dynamo_table(table_name)
            else:
                print("Skipping delete_dynamo_db_table: no table name specified")

        elif task_name == "empty_dynamo_db_table":
            table_name = task.get("table")
            if table_name:
                empty_dynamo_table(table_name)
            else:
                print("Skipping empty_dynamo_db_table: no table name specified")

        elif task_name == "populate_dynamo_db_table":
            table_name = task.get("table")
            data_file = task.get("data_file")
            if table_name and data_file:
                populate_dynamo_table(table_name, data_file)
            else:
                print("Skipping populate_dynamo_db_table: missing table name or data file")

        elif task_name == "create_s3_bucket":
            bucket_name = task.get("bucket")
            if bucket_name:
                create_s3_bucket(bucket_name, task.get("region", "us-east-1"))
            else:
                print("Skipping create_s3_bucket: no bucket name specified")

        elif task_name == "delete_s3_bucket":
            bucket_name = task.get("bucket")
            if bucket_name:
                delete_s3_bucket(bucket_name)
            else:
                print("Skipping delete_s3_bucket: no bucket name specified")

        elif task_name == "empty_s3_bucket":
            bucket_name = task.get("bucket")
            if bucket_name:
                empty_s3_bucket(bucket_name)
            else:
                print("Skipping empty_s3_bucket: no bucket name specified")

        elif task_name == "populate_s3_bucket":
            bucket_name = task.get("bucket")
            folder = task.get("folder")
            if bucket_name and folder:
                populate_s3_bucket(bucket_name, folder)
            else:
                print("Skipping populate_s3_bucket: missing bucket name or folder")

        else:
            print(f"Unknown task: {task_name}")

if __name__ == "__main__":
    main()