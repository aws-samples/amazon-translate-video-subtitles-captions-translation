#!/bin/bash
set -eo pipefail
ARTIFACT_BUCKET=$(cat bucket-name.txt)
TEMPLATE=translate-captions-template.yaml
sam build -t $TEMPLATE
cd .aws-sam/build

sam package --debug  --s3-bucket $ARTIFACT_BUCKET --output-template-file translate-captions-template-cf.yml
sam deploy --debug --template-file translate-captions-template-cf.yml --stack-name translate-captions-stack --capabilities CAPABILITY_NAMED_IAM
