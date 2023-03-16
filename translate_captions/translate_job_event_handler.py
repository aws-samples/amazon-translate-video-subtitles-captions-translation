## Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: MIT-0
import json
import logging
import os
import sys
from urllib.parse import urlparse
from botocore.exceptions import ClientError
from helper import FileHelper,S3Helper,AwsHelper
from captions_helper import Captions

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def processRequest(request):
    output = ""
    logger.info("request: {}".format(request))
    up = urlparse(request["s3uri"], allow_fragments=False)
    accountid = request["accountId"]
    jobid =  request["jobId"]
    bucketName = up.netloc
    objectkey = up.path.lstrip('/')
    basePrefixPath = objectkey 
    languageCode = request["langCode"]
    logger.debug("Base Prefix Path:{}".format(basePrefixPath))
    captions = Captions()
    #filter only the delimited files with .delimited suffix
    objs = S3Helper().getFilteredFileNames(bucketName,basePrefixPath,["delimited"])
    for obj in objs:
        try:
            #Read the Delimited file contents
            content = S3Helper().readFromS3(bucketName,obj)
            fileName = FileHelper().getFileName(obj)
            sourceFileName = FileHelper().getFileName(obj.replace("{}.".format(languageCode),"",1))
            logger.debug("SourceFileKey:{}.processed".format(sourceFileName))
            soureFileKey = "input/{}.processed".format(sourceFileName)
            vttObject = {}
            vttObject["Bucket"] = bucketName
            vttObject["Key"] = soureFileKey
            captions_list = []
            #Based on the file format, call the right method to load the file as python object
            if(fileName.endswith("vtt")):
                    captions_list =  captions.vttToCaptions(vttObject)
            elif(fileName.endswith("srt")):
                captions_list =  captions.srtToCaptions(vttObject)
            # Replace the text captions with the translated content
            translatedCaptionsList = captions.DelimitedToWebCaptions(captions_list,content,"<span>",15)
            translatedText = ""
            # Recreate the Caption files in VTT or SRT format
            if(fileName.endswith("vtt")):
                translatedText =  captions.captionsToVTT(translatedCaptionsList)
            elif(fileName.endswith("srt")):
                translatedText =  captions.captionsToSRT(translatedCaptionsList)
            logger.debug(translatedText)
            logger.debug(content)
            newObjectKey = "output/{}".format(fileName)
            # Write the VTT or SRT file into the output S3 folder
            S3Helper().writeToS3(str(translatedText),bucketName,newObjectKey)   
            output = "Output Object: {}/{}".format(bucketName, newObjectKey)
            logger.debug(output)
        except ClientError as e:
            logger.error("An error occured with S3 bucket operations: %s" % e)
        except :
            e = sys.exc_info()[0]
            logger.error("Error occured processing the captions file: %s" % e)
    objs = S3Helper().getFilteredFileNames(bucketName,"captions-in/",["delimited"])
    if( request["delete_captionsin"] and request["delete_captionsin"] == "true") :
        for obj in objs:
            try:
                logger.debug("Deleting temp delimited caption files {}".format(obj))
                S3Helper().deleteObject(bucketName,obj)
            except ClientError as e:
                logger.error("An error occured with S3 bucket operations: %s" % e)
            except :
                e = sys.exc_info()[0]
                logger.error("Error occured in deleting the delimited captions file: %s" % e)


def lambda_handler(event, context):
    logger.setLevel(logging.DEBUG)
    logger.info("event: {}".format(event))
    request = {}
    statusCode = "200"
    message ="success"
    request["delete_captionsin"] = os.environ["DELETE_INTERMEDIATE_FILES"]
    try:
        jobId = event["detail"]["jobId"]
        translate_client = AwsHelper().getClient('translate')
        response = translate_client.describe_text_translation_job(JobId=jobId)
        logger.info("response: {}".format(response))
        request["s3uri"] =  response['TextTranslationJobProperties']['OutputDataConfig']['S3Uri']
        request["jobId"] = response['TextTranslationJobProperties']['JobId']
        request["jobName"] = response['TextTranslationJobProperties']['JobName']
        status = response['TextTranslationJobProperties']['JobStatus']
        request["langCode"] = response['TextTranslationJobProperties']['TargetLanguageCodes'][0]
        request["accountId"] = context.invoked_function_arn.split(":")[4]
        if status == "COMPLETED" and 'TranslateJob-captions' in response['TextTranslationJobProperties']['JobName'] :
            processRequest(request)
        elif status in ["FAILED", "COMPLETED_WITH_ERROR"]:
            statusCode ="500"
            message = "Translation Job failed"
            logger.warn("Job ID {} failed or completed with errors, exiting".format(request["jobId"]))
    except ValueError:
        statusCode ="500"
        message = "Error converting the XML document"
        logger.error("Error occured loading the json from event:{}".format(event))
    return {
            "statusCode": statusCode,
            "body": json.dumps(message)
        }