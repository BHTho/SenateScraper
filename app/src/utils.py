import os
import boto3
import datetime

def get_dynamodb():
    assert os.getenv('AWS_ACCESS_KEY') is not None, "AWS_ACCESS_KEY environment variable is not set."
    assert os.getenv('AWS_SECRET_KEY') is not None, "AWS_SECRET_KEY environment variable is not set."
    assert os.getenv('AWS_REGION') is not None, "AWS_REGION environment variable is not set."
    return boto3.resource(
        'dynamodb',
        region_name=os.getenv('AWS_REGION'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
    )


def get_inverted_sk_date(record_date: str, identifier: str) -> str:
    """
    Creates an inverted sort key prefix for a DynamboDB item

    Args:
        record_date (str): timestamp of scrape
        identifier (str): unique part of the SK (e.g., "#COMMMITTEE#HEALTH")

    Returns:
        str: Inverted sort key prefix in the format "DATE#<inverted_timestamp><identifier>"
    """
    MAX_TIMESTAMP_MS = 253402300799999 # 9999-12-31
    dt = datetime.strptime(record_date, "%Y-%m-%d")
    timestamp_ms = int(dt.timestamp() * 1000)
    inverted_timestamp = MAX_TIMESTAMP_MS - timestamp_ms
    inverted_sk_prefix = f"DATE#{inverted_timestamp:018d}"
    return f"{inverted_sk_prefix}{identifier}"