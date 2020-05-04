import json
import boto3
import os
import time
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


def detect_labels(photo, bucket):

    client=boto3.client('rekognition')

    response = client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':photo}},
        MaxLabels=10)
    #print (response)
    # print('Detected labels for ' + photo) 
    # print()   
    # for label in response['Labels']:
    #     print ("Label: " + label['Name'])
    #     print ("Confidence: " + str(label['Confidence']))
    #     print ("Instances:")
    #     for instance in label['Instances']:
    #         print ("  Bounding box")
    #         print ("    Top: " + str(instance['BoundingBox']['Top']))
    #         print ("    Left: " + str(instance['BoundingBox']['Left']))
    #         print ("    Width: " +  str(instance['BoundingBox']['Width']))
    #         print ("    Height: " +  str(instance['BoundingBox']['Height']))
    #         print ("  Confidence: " + str(instance['Confidence']))
    #         print()

    #     print ("Parents:")
    #     for parent in label['Parents']:
    #         print ("   " + parent['Name'])
    #     print ("----------")
    #     print ()
    #return len(response['Labels'])
    res = []
    for item in response['Labels']:
        res.append(item['Name'])
    return res



def lambda_handler(event, context):
    print(event)
    # get bucket and photo name
    bucket = event['Records'][0]['s3']['bucket']['name']
    photo = event['Records'][0]['s3']['object']['key']
    # photo='images/orange_cat_1-1588193841880.jpg'
    # bucket='p3b2'
    
    # tag photo, store result as list
    labels_res = detect_labels(photo,bucket)
    # try:
    #     labels_res = detect_labels(photo,bucket)
    # except Exception as err:
    #     print("cannot tag!",err)
    
    print(labels_res)
    
    # print("## variables:")
    # print(os.environ) 
    # print('## Event')
    # print(event)
    
    # connect to vpc
    host = 'vpc-photos2-wc7ewp7gezc7jkxe5sumk4wxni.us-east-1.es.amazonaws.com' 
    # host = 'vpc-photos4-qircgu67ftakri6xjsbsuvwqca.us-east-1.es.amazonaws.com'
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
    
    # create doc
    document = {
        "objectkey": photo[7:],
        "bucket": bucket,
        "createdTimestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "labels": labels_res
    }
    
    print(document)
    
    # #clear es
    # try: 
    #     es.indices.delete(index='photos')
    # except:
    #     pass
    # # es.indices.delete(index='movies')

    # es.indices.create(index='photos')

    # try: 
    #     es.indices.refresh(index='photos')
    # except:
    #     pass
    
    # insert doc to es
    response = es.index(index="photos", doc_type="_doc", id=photo[7:] , body=document)
    print (response)

    
    return {
        'statusCode': 200,
        'body': str(response)
    }
    
    
    
