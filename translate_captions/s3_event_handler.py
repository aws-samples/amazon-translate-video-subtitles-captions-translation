## Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: MIT-0

import json
import logging
import os
from botocore.exceptions import ClientError
from helper import FileHelper,S3Helper,AwsHelper
from captions_helper import Captions

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
def processRequest(request):
    output = ""
    logger.info("request: {}".format(request))

    bucketName = request["bucketName"]
    sourceLanguageCode = request["sourceLanguage"]
    targetLanguageCode = request["targetLanguage"]
    access_role = request["access_role"]
    triggerFile = request["trigger_file"]
    try:
        captions = Captions()
        #filter only the VTT and SRT file for processing in the input folder
        objs = S3Helper().getFilteredFileNames(bucketName,"input/",["vtt","srt"])
        for obj in objs:
            try:
                vttObject = {}
                vttObject["Bucket"] = bucketName
                vttObject["Key"] = obj
                captions_list =[]
                #based on the file type call the method that coverts them into python list object
                if(obj.endswith("vtt")):
                    captions_list =  captions.vttToCaptions(vttObject)
                elif(obj.endswith("srt")):
                    captions_list =  captions.srtToCaptions(vttObject)
                #convert the text captions in the list object to a delimited file
                delimitedFile = captions.ConvertToDemilitedFiles(captions_list)
                fileName = obj.split("/")[-1]
                newObjectKey = "captions-in/{}.delimited".format(fileName)
                S3Helper().writeToS3(str(delimitedFile),bucketName,newObjectKey)   
                output = "Output Object: {}/{}".format(bucketName, newObjectKey)
                logger.debug(output)
                S3Helper().renameObject(bucketName,obj,"{}.processed".format(obj))
            except ClientError as e:
                logger.error("An error occured starting the Translate Batch Job: %s" % e)
        translateContext = {}
        translateContext["sourceLang"] = sourceLanguageCode
        translateContext["targetLangList"] = [targetLanguageCode]
        translateContext["roleArn"] = access_role 
        translateContext["bucket"] = bucketName
        translateContext["inputLocation"] = "captions-in/"
        translateContext["outputlocation"] = "captions-out/"
        translateContext["jobPrefix"] = "TranslateJob-captions"
        #Call Amazon Translate to translate the delimited files in the captions-in folder
        jobinfo = captions.TranslateCaptions(translateContext)
        S3Helper().deleteObject(bucketName,"input/{}".format(triggerFile))
        logger.debug(jobinfo)
    except ClientError as e:
        logger.error("An error occured with S3 Bucket Operation: %s" % e)

def lambda_handler(event, context):
    logger.setLevel(logging.DEBUG)
    logger.info("event: {}".format(event))
    request = {}
    request["bucketName"] = event['Records'][0]['s3']['bucket']['name']
    request["sourceLanguage"] = os.environ['SOURCE_LANG_CODE']
    request["targetLanguage"] = os.environ['TARGET_LANG_CODE']
    request["access_role"] = os.environ['S3_ROLE_ARN']
    request["trigger_file"] = os.environ['TRIGGER_NAME']
    processRequest(request)
    return {
        "statusCode": 200,
        "body": json.dumps('success')
    }
