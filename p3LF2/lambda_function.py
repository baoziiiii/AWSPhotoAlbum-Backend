import json
import boto3
import base64
import os
import time
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

s3 = boto3.client("s3")

def list_picture(key,labels): 
    r = {}
    # label = ''.join(key.rsplit(key.split("-")[-1],1))[:-1].replace('images/','',1) # TOCHANGE: label暂时是从文件名提取
    # r['Label'] = label
    
    # concat labels list to string
    label_string = ','.join(labels)
    r['Label'] = label_string
    # replace blank space to +
    key = key.replace(" ", "+")
    r['Path'] = 'https://p3b2.s3.amazonaws.com/images/'+key
    return r



## IMPORTANT: get picture raw binary data
def get_raw_picture(key):
    r =  s3.get_object(
        Bucket='p3b2',
        Key = key
    )
    if r and r['Body']:
        return base64.b64decode(str(r['Body'].read()).split(',')[-1])
    return None


def list_all_pictures(prefix = 'images/',maxkeys = 100, reset = True, key_word=''):
    if reset:
        del images[:]
    # response = s3.list_objects(
    #     Bucket='p3b2',
    #     MaxKeys=maxkeys,
    #     Prefix=prefix,
    # )
    # for content in response["Contents"]:
    #     key = content["Key"]
    #     if key != 'images/':
    #         images.append(list_picture(key))
    
    # connect to vpc
    host = 'vpc-photos2-wc7ewp7gezc7jkxe5sumk4wxni.us-east-1.es.amazonaws.com' 
    region = 'us-east-1' # e.g. us-west-1
    
    # connect to es
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    
    es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    
   
    # change key_word to from list to string
    #search_word=' '.join(key_word)
    # search key_word as tag 
    query_body = {
      "size": 20,
      "query": {
        "query_string": {
          "query": key_word,
          "default_field": "labels"
        }
      }
    }
    
    # check all records in es
    #print(es.indices.get_alias("*") )
    
    # search tag
    res = es.search(index="photos", body=query_body)
    #print (res)
    
   # for content in response["Contents"]:
        # key = content["Key"]
        # if key != 'images/':
    for records in res['hits']['hits']:
        key = records['_source']['objectkey']
        #print(key)
        labels = records['_source']['labels']
        images.append(list_picture(key,labels))
        
    # print("images:",images)
    return images

images = [] 

def lambda_handler(event, context):
    
    print(event)
    
    # TODO implement
    # print(event)


    query_text = event["queryStringParameters"]["q"]
    #print(query_text) # it's query string
    
    search_res = list_all_pictures(reset=True,key_word=query_text)
    
    print("all search photos:",images)
    
    returnBody = {
        "imagePaths":images
    }
    
    return {
        'statusCode': 200,
        'headers': {
            "Content-Type" : "application/json",
            "Access-Control-Allow-Origin" : "*",
            "Allow" : "GET, OPTIONS, POST",
            "Access-Control-Allow-Methods" : "GET, OPTIONS, POST",
            "Access-Control-Allow-Headers" : "*"
        },
        'body': str(returnBody)
    }
