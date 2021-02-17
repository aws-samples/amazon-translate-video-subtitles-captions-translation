## Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: MIT-0

import boto3
from botocore.client import Config
import os
import io


class AwsHelper:
    def getClient(self, name, awsRegion=None):
        config = Config(
            retries = dict(
                max_attempts = 6
            )
        )
        if(awsRegion):
            return boto3.client(name, region_name=awsRegion, config=config)
        else:
            return boto3.client(name, config=config)

    def getResource(self, name, awsRegion=None):
        config = Config(
            retries = dict(
                max_attempts = 6
            )
        )

        if(awsRegion):
            return boto3.resource(name, region_name=awsRegion, config=config)
        else:
            return boto3.resource(name, config=config)

class S3Helper:
    @staticmethod
    def getS3BucketRegion(bucketName):
        client = boto3.client('s3')
        response = client.get_bucket_location(Bucket=bucketName)
        awsRegion = response['LocationConstraint']
        return awsRegion

    @staticmethod
    def getFileNames(bucketName, prefix, maxPages, allowedFileTypes, awsRegion=None):

        files = []

        currentPage = 1
        hasMoreContent = True
        continuationToken = None

        s3client = AwsHelper().getClient('s3', awsRegion)

        while(hasMoreContent and currentPage <= maxPages):
            if(continuationToken):
                listObjectsResponse = s3client.list_objects_v2(
                    Bucket=bucketName,
                    Prefix=prefix,
                    ContinuationToken=continuationToken)
            else:
                listObjectsResponse = s3client.list_objects_v2(
                    Bucket=bucketName,
                    Prefix=prefix)

            if(listObjectsResponse['IsTruncated']):
                continuationToken = listObjectsResponse['NextContinuationToken']
            else:
                hasMoreContent = False

            for doc in listObjectsResponse['Contents']:
                docName = doc['Key']
                docExt = FileHelper.getFileExtenstion(docName)
                docExtLower = docExt.lower()
                if(docExtLower in allowedFileTypes):
                    files.append(docName)

        return files
    @staticmethod
    def getFilteredFileNames(bucketName, prefix, extensions, awsRegion=None):
        files = []
        s3client = AwsHelper().getResource('s3', awsRegion)
        bucket = s3client.Bucket(bucketName)
        objs = bucket.objects.filter(Prefix=prefix)
        for obj in objs:
            docName = obj.key
            docExt = FileHelper.getFileExtenstion(docName)
            docExtLower = docExt.lower()
            print("Key:{}".format(docName))
            if (docExtLower in extensions):
               files.append(docName)
        return files

    @staticmethod
    def writeToS3(content, bucketName, s3FileName, awsRegion=None):
        s3 = AwsHelper().getResource('s3', awsRegion)
        object = s3.Object(bucketName, s3FileName)
        object.put(Body=content)

    @staticmethod
    def readFromS3(bucketName, s3FileName, awsRegion=None):
        s3 = AwsHelper().getResource('s3', awsRegion)
        obj = s3.Object(bucketName, s3FileName)
        return obj.get()['Body'].read().decode('utf-8')
    
    @staticmethod
    def deleteObject(bucketName, s3FileName, awsRegion=None):
        s3 = AwsHelper().getResource('s3', awsRegion)
        obj = s3.Object(bucketName, s3FileName)
        return obj.delete()

    @staticmethod
    def renameObject(bucketName, current, newObject, awsRegion=None):
        print("Renaming object {} to {} in bucket {}".format(current,newObject,bucketName))
        s3 = AwsHelper().getResource('s3', awsRegion)
        s3.Object(bucketName, newObject).copy_from(CopySource=bucketName+"/"+current)
        s3.Object(bucketName,current).delete()

class FileHelper:
    @staticmethod
    def getFileNameAndExtension(filePath):
        basename = os.path.basename(filePath)
        dn, dext = os.path.splitext(basename)
        return (dn, dext[1:])

    @staticmethod
    def getFileName(fileName):
        basename = os.path.basename(fileName)
        dn, dext = os.path.splitext(basename)
        return dn

    @staticmethod
    def getFileExtenstion(fileName):
        basename = os.path.basename(fileName)
        dn, dext = os.path.splitext(basename)
        return dext[1:]
