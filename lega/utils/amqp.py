import logging
import pika
import json
import uuid

from ..conf import CONF

LOG = logging.getLogger('amqp')

def get_connection(domain, blocking=True):
    '''
    Returns a blocking connection to the Message Broker supporting AMQP(S).
    
    The host, portm virtual_host, username, password and
    heartbeat values are read from the CONF argument.
    So are the SSL options.
    '''
    assert domain in CONF.sections(), "Section not found in config file"

    params = {
        'host': CONF.get(domain,'host',fallback='localhost'),
        'port': CONF.getint(domain,'port',fallback=5672),
        'virtual_host': CONF.get(domain,'vhost',fallback='/'),
        'credentials': pika.PlainCredentials(
            CONF.get(domain,'username'),
            CONF.get(domain,'password')
        ),
        'connection_attempts': CONF.getint(domain,'connection_attempts',fallback=2),
    }
    heartbeat = CONF.getint(domain,'heartbeat', fallback=None)
    if heartbeat is not None: # can be 0
        # heartbeat_interval instead of heartbeat like they say in the doc
        # https://pika.readthedocs.io/en/latest/modules/parameters.html#connectionparameters
        params['heartbeat_interval'] = heartbeat
        LOG.debug(f'Setting hearbeat to {heartbeat}')

    # SSL configuration
    if CONF.getboolean(domain,'enable_ssl', fallback=False):
        params['ssl'] = True
        params['ssl_options'] = {
            'ca_certs' : CONF.get(domain,'cacert'),
            'certfile' : CONF.get(domain,'cert'),
            'keyfile'  : CONF.get(domain,'keyfile'),
            'cert_reqs': 2, #ssl.CERT_REQUIRED is actually <VerifyMode.CERT_REQUIRED: 2>
        }

    LOG.info(f'Getting a connection to {domain}')
    LOG.debug(params)

    if blocking:
        return pika.BlockingConnection( pika.ConnectionParameters(**params) )
    return pika.SelectConnection( pika.ConnectionParameters(**params) )

def publish(message, channel, exchange, routing, correlation_id=None):
    '''
    Sending a message to the local broker with `path` was updated
    '''
    LOG.debug(f'Sending {message} to exchange: {exchange} [routing key: {routing}]')
    channel.basic_publish(exchange    = exchange,
                          routing_key = routing,
                          body        = json.dumps(message),
                          properties  = pika.BasicProperties(correlation_id=correlation_id or str(uuid.uuid4()),
                                                             content_type='application/json',
                                                             delivery_mode=2))
    

def consume(work, from_queue, to_routing):
    '''Blocking function, registering callback `work` to be called.

    from_broker must be a pair (from_connection: pika:Connection, from_queue: str)
    to_broker must be a triplet (to_connection: pika:Connection, to_exchange: str, to_routing: str)

    If there are no message in `from_queue`, the function blocks and
    waits for new messages.

    If the function `work` returns a non-None message, the latter is
    published to the exchange `to_exchange` with `to_routing` as the
    routing key.
    '''

    assert( from_queue and to_routing )
    connection = get_connection('broker')

    LOG.debug(f'Consuming message from {from_queue}')

    from_channel = connection.channel()
    from_channel.basic_qos(prefetch_count=1) # One job per worker
    to_channel = connection.channel()

    def process_request(channel, method_frame, props, body):
        correlation_id = props.correlation_id
        message_id = method_frame.delivery_tag
        LOG.debug(f'Consuming message {message_id} (Correlation ID: {correlation_id})')

        # Process message in JSON format
        answer = work( json.loads(body) ) # Exceptions should be already caught

        # Publish the answer
        if answer:
            publish(answer, to_channel, 'lega', to_routing, correlation_id = props.correlation_id)

        # Acknowledgment: Cancel the message resend in case MQ crashes
        LOG.debug(f'Sending ACK for message {message_id} (Correlation ID: {correlation_id})')
        channel.basic_ack(delivery_tag=method_frame.delivery_tag)        
            
    # Let's do this
    try:
        from_channel.basic_consume(process_request, queue=from_queue)
        from_channel.start_consuming()
    except KeyboardInterrupt:
        from_channel.stop_consuming()
    finally:
        connection.close()

