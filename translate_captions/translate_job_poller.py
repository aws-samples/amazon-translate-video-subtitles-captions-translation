## Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: MIT-0

import boto3
import logging
import os

from botocore.exceptions import ClientError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def msgpublish(jobid):
    client = boto3.client('translate')
    try:
        response = client.describe_text_translation_job(JobId=jobid)
        logger.debug('Job Status is: {}' .format(response['TextTranslationJobProperties']['JobStatus']))
        return(response['TextTranslationJobProperties']['JobStatus'])
    
    except ClientError as e:
        logger.error("An error occured: %s" % e)
    
def lambda_handler(event, context):
    logger.setLevel(logging.DEBUG)
    logger.debug('Job ID is: {}' .format(event))
    return(msgpublish(event))