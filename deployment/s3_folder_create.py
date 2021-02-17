## Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: MIT-0

import boto3
import logging
import json
import cfnresponse

s3Client = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def create(properties, physical_id):
    bucketName = properties['S3Bucket']
    s3Client.put_object(Bucket=bucketName, Key=('input/'))
    s3Client.put_object(Bucket=bucketName, Key=('output/'))
    s3Client.put_object(Bucket=bucketName, Key=('captions-in/'))
    s3Client.put_object(Bucket=bucketName, Key=('captions-out/'))
    return cfnresponse.SUCCESS, physical_id


def update(properties, physical_id):
    return cfnresponse.SUCCESS, None


def delete(properties, physical_id):
    return cfnresponse.SUCCESS, None


def handler(event, context):
    logger.info('Received event: %s' % json.dumps(event))
    status = cfnresponse.FAILED
    new_physical_id = None
    try:
        properties = event.get('ResourceProperties')
        physical_id = event.get('PhysicalResourceId')
        status, new_physical_id = {'Create': create, 'Update': update, 'Delete':
                                    delete}.get(event['RequestType'], lambda x, y: (cfnresponse.FAILED,
                                                                                    None))(properties, physical_id)
    except Exception as e:
        logger.error('Exception:%s' % e)
        status = cfnresponse.FAILED
    finally:
        cfnresponse.send(event, context, status, {}, new_physical_id)