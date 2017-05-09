#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
####################################
#
# Listener moving files to the Vault
#
####################################

It simply consumes message from the message queue configured in the [vault] section.

It defaults to the `completed` queue.

When a message is consumed, it must be of the form:
* filepath
* submission_id
* user_id

This service should probably also implement a stort of StableID generator,
and input that in the database.
'''

import sys
import os
import logging
import json
import traceback
from pathlib import Path
import requests

from .conf import CONF
from . import crypto
from . import amqp as broker
from . import utils

LOG = logging.getLogger('vault')

def work(message_id, body):
    '''Procedure to handle a message'''

    LOG.debug(f"Processing message: {message_id}")
    try:

        data = json.loads(body)

        submission_id = data['submission_id']
        user_id       = data['user_id']
        filepath      = Path(data['filepath'])

        vault_area = Path( CONF.get('vault','location') )
        
        req = requests.get(CONF.get('namer','location'),
                           headers={'X-LocalEGA-Sweden':'yes'})
        name = req.text.strip()
        name_bits = [name[i:i+3] for i in range(0, len(name), 3)]

        LOG.debug(f'Name bits: {name_bits!r}')
        target = vault_area.joinpath(*name_bits)
        LOG.debug(f'Target: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        LOG.debug('Target parent: {}'.format(target.parent))
        filepath.rename( target ) # move

        # remove it empty
        try:
            filepath.parent.rmdir()
            LOG.debug('Removing {}'.format(filepath.parent))
        except OSError:
            pass
            
        # Mark it as processed in DB
        # TODO

        return None

    except Exception as e:
        LOG.debug(f"{e.__class__.__name__}: {e!s}")
        #if isinstance(e,crypto.Error) or isinstance(e,OSError):
        traceback.print_exc()
        raise e


def main(args=None):

    if not args:
        args = sys.argv[1:]

    CONF.setup(args) # re-conf

    broker.consume( work,
                    from_queue = CONF.get('vault','message_queue'))

if __name__ == '__main__':
    main()