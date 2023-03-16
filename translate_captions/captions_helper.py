## Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: MIT-0

import boto3
import logging
import math
import html
import time
import webvtt
from io import StringIO
from helper import AwsHelper,S3Helper
from tempfile import NamedTemporaryFile

class Captions:

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def ConvertToDemilitedFiles(self,inputCaptions):
        marker = "<span>"
        # Convert captions to text with marker between caption lines
        inputEntries = map(lambda c: c["caption"], inputCaptions)
        inputDelimited = marker.join(inputEntries)
        self.logger.debug(inputDelimited)
        return inputDelimited

    def TranslateCaptions(self, translationContext, terminology_names=[]):

        marker = "<span>"
        sourceLanguageCode = translationContext["sourceLang"]
        targetLanguageCodes = translationContext["targetLangList"]
        translate_role= translationContext["roleArn"]
        bucket = translationContext["bucket"] 
        inputPath = translationContext["inputLocation"] 
        outputPath= translationContext["outputlocation"]
        jobPrefix = translationContext["jobPrefix"]
        try:
            translate_client =AwsHelper().getClient('translate')
            targetLanguageCode = targetLanguageCodes[0]
            self.logger.debug("Starting translation to {}".format(targetLanguageCode))
            singletonTargetList = []
            singletonTargetList.append(targetLanguageCode)
            millis = int(round(time.time() * 1000))
            job_name = jobPrefix+ str(millis)
            self.logger.debug("JobName: {}".format(job_name))

            terminology_name = []
            if len(terminology_names) > 0:
                for item in terminology_names:
                    if targetLanguageCode in item['TargetLanguageCodes']:
                        terminology_name.append(item['Name'])
                        break
                if len(terminology_name) == 0:
                    self.logger.debug(int("No custom terminology specified."))
                else:
                    self.logger.debug("Using custom terminology {}".format(terminology_name))

            # Save the delimited transcript text to S3
            response = translate_client.start_text_translation_job(
                JobName=job_name,
                InputDataConfig={
                    'S3Uri': "s3://{}/{}".format(bucket,inputPath),
                    'ContentType': "text/html"
                },
                OutputDataConfig={
                    'S3Uri': "s3://{}/{}".format(bucket,outputPath)
                },
                DataAccessRoleArn=translate_role,
                SourceLanguageCode=sourceLanguageCode,
                TargetLanguageCodes=singletonTargetList,
                TerminologyNames=terminology_name
            )
            jobinfo = {
                "JobId": response["JobId"],
                "TargetLanguageCode": targetLanguageCode
            }
            return jobinfo

        except Exception as e:
            self.logger.error(e)
            raise e

    def captionsToSRT(self, captions):
        srt = ''

        index = 1

        for caption in captions:
            srt += str(index) + '\n'
            srt += self.formatTimeSRT(float(caption["start"])) + ' --> ' + self.formatTimeSRT(float(caption["end"])) + '\n'
            srt += caption["caption"] + '\n\n'
            index += 1

        return srt.rstrip()

    def captionsToVTT(self, captions):
        vtt = 'WEBVTT\n\n'

        for caption in captions:
            vtt += self.formatTimeVTT(float(caption["start"])) + ' --> ' + self.formatTimeVTT(float(caption["end"])) + '\n'
            vtt += caption["caption"] + '\n\n'

        return vtt.rstrip()

    # Converts a delimited file back to web captions format.
    # Uses the source web captions to get timestamps and source caption text (saved in sourceCaption field).
    def DelimitedToWebCaptions(self, sourceWebCaptions, delimitedCaptions, delimiter, maxCaptionLineLength):

        delimitedCaptions = html.unescape(delimitedCaptions)

        entries = delimitedCaptions.split(delimiter)

        outputWebCaptions = []
        for i, c in enumerate(sourceWebCaptions):
            caption = {}
            caption["start"] = c["start"]
            caption["end"] = c["end"]
            caption["caption"] = entries[i]
            caption["sourceCaption"] = c["caption"]
            outputWebCaptions.append(caption)

        return outputWebCaptions
    
    # Convert VTT to WebCaptions
    def vttToCaptions(self, vttObject):

        captions = []
        vtt = ""
        # Get metadata
        s3 = boto3.client('s3')
        try:
            self.logger.debug("Getting data from s3://"+vttObject["Bucket"]+"/"+vttObject["Key"])
            vtt = S3Helper().readFromS3(vttObject["Bucket"], vttObject["Key"])
            self.logger.debug(vtt)
        except Exception as e:
            #Fix me
             self.logger.error(e)

        buffer = StringIO(vtt)

        for vttcaption in webvtt.read_buffer(buffer):
            caption = {}
            caption["start"] = self.formatTimeVTTtoSeconds(vttcaption.start)
            caption["end"] = self.formatTimeVTTtoSeconds(vttcaption.end)
            caption["caption"] = vttcaption.text
            captions.append(caption)

        return captions
    # Convert VTT to WebCaptions
    def srtToCaptions(self, vttObject):

        captions = []
        srt = ""
        # Get metadata
        s3 = boto3.client('s3')
        try:
            self.logger.debug("Getting data from s3://"+vttObject["Bucket"]+"/"+vttObject["Key"])
            srt = S3Helper().readFromS3(vttObject["Bucket"], vttObject["Key"])
            self.logger.debug(srt)
        except Exception as e:
            raise e
        #buffer = StringIO(srt)
        f = NamedTemporaryFile(mode='w+', delete=False)
        f.write(srt)
        f.close()
        for srtcaption in webvtt.from_srt(f.name):
            caption = {}
            self.logger.debug(srtcaption)
            caption["start"] = self.formatTimeVTTtoSeconds(srtcaption.start)
            caption["end"] = self.formatTimeVTTtoSeconds(srtcaption.end)
            caption["caption"] = srtcaption.text
            self.logger.debug("Caption Object:{}".format(caption))
            captions.append(caption)

        return captions

    # Format an SRT timestamp in HH:MM:SS,mmm
    def formatTimeSRT(self, timeSeconds):
        ONE_HOUR = 60 * 60
        ONE_MINUTE = 60
        hours = math.floor(timeSeconds / ONE_HOUR)
        remainder = timeSeconds - (hours * ONE_HOUR)
        minutes = math.floor(remainder / 60)
        remainder = remainder - (minutes * ONE_MINUTE)
        seconds = math.floor(remainder)
        remainder = remainder - seconds
        millis = remainder
        return str(hours).zfill(2) + ':' + str(minutes).zfill(2) + ':' + str(seconds).zfill(2) + ',' + str(math.floor(millis * 1000)).zfill(3)

    # Format a VTT timestamp in HH:MM:SS.mmm
    def formatTimeVTT(self, timeSeconds):
        ONE_HOUR = 60 * 60
        ONE_MINUTE = 60
        hours = math.floor(timeSeconds / ONE_HOUR)
        remainder = timeSeconds - (hours * ONE_HOUR)
        minutes = math.floor(remainder / 60)
        remainder = remainder - (minutes * ONE_MINUTE)
        seconds = math.floor(remainder)
        remainder = remainder - seconds
        millis = remainder
        return str(hours).zfill(2) + ':' + str(minutes).zfill(2) + ':' + str(seconds).zfill(2) + '.' + str(math.floor(millis * 1000)).zfill(3)


    # Format a VTT timestamp in HH:MM:SS.mmm
    def formatTimeVTTtoSeconds(self,timeHMSf):
        hours, minutes, seconds = (timeHMSf.split(":"))[-3:]
        hours = int(hours)
        minutes = int(minutes)
        seconds = float(seconds)
        timeSeconds = float(3600 * hours + 60 * minutes + seconds)
        return str(timeSeconds)


