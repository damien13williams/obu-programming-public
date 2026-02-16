import boto3
from config import REGION

dynamodb = boto3.resource('dynamodb', region_name=REGION)
client = boto3.client("dynamodb", region_name=REGION)

