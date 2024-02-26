import os
import argparse
import boto3
from dotenv import load_dotenv

load_dotenv()

DEFAULT_POLICY_NAME = "Soliseco-P1-Policy"
DEFAULT_BUCKET_NAME = "soliseco-p1-credentials"

parser = argparse.ArgumentParser(
    prog="IoT Core Provisioning",
    description="Provision device on AWS IoTCore"
)
parser.add_argument('--thing-name', dest="thing_name", required=True)
parser.add_argument('--policiy-name', dest="policy_name", default=DEFAULT_POLICY_NAME)
parser.add_argument('--output-dir', dest="output_dir", default="./")
parser.add_argument('--bucket-name', dest="bucket_name", default=DEFAULT_BUCKET_NAME)
parser.add_argument('--local-save', dest="local_save", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument('--s3-save', dest="s3_save", action=argparse.BooleanOptionalAction, default=True)

args = parser.parse_args()

THING_NAME = args.thing_name
POLICY_NAME = args.policy_name
OUTPUT_DIR = args.output_dir
BUCKET_NAME = args.bucket_name
LOCAL_SAVE = args.local_save
S3_SAVE = args.s3_save

session = boto3.Session(region_name='eu-central-1')

iot_client = session.client('iot')
s3 = session.resource('s3')


def create_thing(thing_name, policy_name):
    try:
        # Check if thing already exists
        iot_client.describe_thing(thingName=thing_name)
    except iot_client.exceptions.ResourceNotFoundException:
        # Create thing corresponding to sensor
        iot_client.create_thing(thingName=thing_name)
    else:
        raise Exception('Thing already exists')

    cert_and_keys = iot_client.create_keys_and_certificate(setAsActive=True)
    certificate_arn = cert_and_keys['certificateArn']
    certificate = cert_and_keys['certificatePem']
    pub_key = cert_and_keys['keyPair']['PublicKey']
    private_key = cert_and_keys['keyPair']['PrivateKey']
    iot_client.attach_policy(policyName=policy_name, target=certificate_arn)
    iot_client.attach_thing_principal(thingName=thing_name, principal=certificate_arn)
    return certificate, private_key, pub_key


def save_to_s3(thing_name, bucket_name, certificate, private_key, pub_key):
    cert_obj_key = thing_name + '/' + thing_name + '.cert.pem'
    cert_object = s3.Object(bucket_name, cert_obj_key)
    cert_object.put(Body=certificate)

    private_key_obj_key = thing_name + '/' + thing_name + '.private.key'
    private_key_obj = s3.Object(bucket_name, private_key_obj_key)
    private_key_obj.put(Body=private_key)

    pub_key_obj_key = thing_name + '/' + thing_name + '.public.key'
    pub_key_object = s3.Object(bucket_name, pub_key_obj_key)
    pub_key_object.put(Body=pub_key)


def save_to_fs(thing_name, output_dir, certificate, private_key, pub_key):
    private_key_path = os.path.join(output_dir, thing_name + '.private.key')
    pub_key_path = os.path.join(output_dir, thing_name + '.public.key')
    certiface_path = os.path.join(output_dir, thing_name + '.cert.pem')

    with open(private_key_path, 'w') as file:
        file.write(private_key)

    with open(pub_key_path, 'w') as file:
        file.write(pub_key)

    with open(certiface_path, 'w') as file:
        file.write(certificate)


certificate, private_key, pub_key = create_thing(THING_NAME, POLICY_NAME)

if LOCAL_SAVE:
    save_to_fs(THING_NAME, OUTPUT_DIR, certificate, private_key, pub_key)

if S3_SAVE:
    save_to_s3(THING_NAME, BUCKET_NAME, certificate, private_key, pub_key)
