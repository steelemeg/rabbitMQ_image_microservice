# Based on code from https://www.cloudamqp.com/docs/python.html

import pika, os, json
from datetime import datetime
# Import the parser code and instantiate.
from getGoogleImages import GoogleImages
image_fetcher = GoogleImages()

url = ""

if os.path.isfile('secrets.py'):
    import secrets
    url = secrets.CLOUDAMQP_URL
else:
    # Access the CLOUDAMQP_URL environment variable
    url = os.environ.get('CLOUDAMQP_URL')

params = pika.URLParameters(url)

# Configure the connection.
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.queue_declare(queue='google_images_requests')

def request_logger(*args):
    logfile = open("log.txt", "a")
    logfile.write(str(datetime.today()))
    for each in args:
        logfile.write(str(each).rstrip('\n'))
    logfile.write('\n')
    logfile.close()

def on_request(ch, method, properties, req_body):
    json_response = {'success': True}
    num_images = 10
    # Rough logging
    print(req_body, properties.reply_to)
    request_logger(req_body, properties)
    # Check if the requests body parses as valid JSON.
    try:
        json_request = json.loads(req_body)
    except ValueError as e:
        json_response = {'success': False, 'error_message': 'Request body did not contain not valid JSON'}
    else:
        # Parse the request and prepare the search terms. image_parameters is required, num_images is optional.
        if 'image_parameters' not in json_request:
            json_response = {'success': False, 'error_message': 'Missing image_parameters. This is a required field'}
        if 'num_images' in json_request and not json_request['num_images'].isnumeric():
            json_response = {'success': False, 'error_message': 'Num_images is optional, but must be an integer  \
                                                number if specified.'}
        else:
            if 'num_images' in json_request:
                # add handling here
                num_images = json_request['num_images'] if json_request['num_images'].isnumeric() else 10
            image_parameters = json_request['image_parameters']
            results = image_fetcher.image_query(image_parameters, num_images)
            if results[0] == 'Error':
                json_response = {'success': False, 'error_message': 'Google error encountered'}
                request_logger(results[1])
            else:
                json_response['images'] = results
    finally:
        ch.basic_publish(exchange='',
                         routing_key=properties.reply_to,
                         properties=pika.BasicProperties(correlation_id= \
                                                             properties.correlation_id),
                         body=json.dumps(json_response))
        ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume('google_images_requests', on_message_callback=on_request)

print(' [*] Waiting for messages:')
channel.start_consuming()

connection.close()
