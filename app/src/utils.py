import os
import boto3


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