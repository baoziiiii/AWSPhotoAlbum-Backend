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


def list_all_pictures(key_words, prefix = 'images/',maxkeys = 100, reset = True):
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
    # host = 'vpc-photos2-wc7ewp7gezc7jkxe5sumk4wxni.us-east-1.es.amazonaws.com' 
    host = 'vpc-photos-p6stlstqc4owdhc3u2unxkrhba.us-east-1.es.amazonaws.com'
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
    
   
    # change key_words to from list to string
    #search_word=' '.join(key_words)
    # search key_words as tag 
    print("images:",images)
    print("key_words:",key_words)
    for slot_name, slot_value in key_words.items():
        if slot_value :
            # query_body = {
            #   "size": 20,
            #   "query": {
            #       "fuzzy":{
            #         "query_string": {
            #           "query": slot_value,
            #           "default_field": "labels"
            #           }
            #         }
            #     }
            # }
            query_body = {
              "size": 20,
              "query": {
                  "fuzzy":{
                    "labels": {
                      "value": slot_value
                      }
                    }
                }
            }
            
            # check all records in es
            #print(es.indices.get_alias("*") )
            
            # search tag
            res = es.search(index="photos", body=query_body)
            print ("=========res",res)
        
       # for content in response["Contents"]:
            # key = content["Key"]
            # if key != 'images/':
            for records in res['hits']['hits']:
                key = records['_source']['objectkey']
                #print(key)
                labels = records['_source']['labels']
                print("---keys:",key)
                images.append(list_picture(key,labels))
                print("---images:",images)
        # print("images:",images)
    return images

images = [] 

def lambda_handler(event, context):
    print("EVENT ------{}".format(json.dumps(event)))

    query_text = event['queryStringParameters']['q']
    print("QUERY_TEXT ------{}".format(query_text))
    
    
    key_words = {}
    if len(query_text.split(" ")) > 1:
        #Adding lex to disambiguation query_text
        lex = boto3.client('lex-runtime', region_name = 'us-east-1')

        lex_response = lex.post_text(
            botName = 'PhotoSearchBot',
            botAlias = 'photosearchbot',
            userId ='1234',
            sessionAttributes={},
            requestAttributes={},
            inputText = query_text
        )
        print("LEX RESPONSE OF QUERY ------{}".format(json.dumps(lex_response)))
        
        key_words = lex_response['slots']
    else:
        key_words['q'] = query_text
        
    print("LEX RESPONSE SLOT ------{}".format(json.dumps(key_words)))
    
    #Es search using reponse _lots return value as tag
    search_res = list_all_pictures(key_words=key_words, reset=True)
    print("all search photos:",images)
    
    returnBody = {
        "imagePaths":images
    }
    returnContext = {
        'statusCode': 200,
        'headers': {
            "Content-Type" : "application/json",
            "Access-Control-Allow-Origin" : "*",
            "Allow" : "GET, OPTIONS, POST",
            "Access-Control-Allow-Methods" : "GET, OPTIONS, POST",
            "Access-Control-Allow-Headers" : "*"
        },
        'body': ""
    }
    
    if not returnBody["imagePaths"]:
        returnContext['body'] = json.dumps("No photo found!")
    else:
        returnContext['body'] = str(returnBody)
    
    return returnContext
