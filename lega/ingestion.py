#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
####################################
#
# Ingestion API Front-end
#
####################################

We provide:

|------------------------------|-----------------|----------------|
| endpoint                     | accepted method |     Note       |
|------------------------------|-----------------|----------------|
| [LocalEGA-URL]/              |       GET       |                |
| [LocalEGA-URL]/ingest        |      POST       | requires login |
| [LocalEGA-URL]/create-inbox  |       GET       | requires login |
| [LocalEGA-URL]/status/<name> |       GET       |                |
|------------------------------|-----------------|----------------|

:author: Frédéric Haziza
:copyright: (c) 2017, NBIS System Developers.
'''

import sys
import os
import stat
import logging
import asyncio
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from colorama import Fore, Back
from aiohttp import web
from aiohttp_swaggerify import swaggerify
import aiohttp_cors
import jinja2
import aiohttp_jinja2

from .conf import CONF
from . import amqp as broker
from .db import (Status as db_status,
                 aiodb)
from .utils import (
    get_data as parse_data,
    only_central_ega,
    get_inbox,
    get_staging_area,
    checksum
)

LOG = logging.getLogger('ingestion')

@aiohttp_jinja2.template('index.html')
async def index(request):
    '''Main endpoint with documentation

    The template is `index.html` in the configured template folder.
    '''
    #return web.Response(text=f'\n{Fore.BLACK}{Back.YELLOW}GOOOoooooodddd morning, Vietnaaaam!{Back.RESET}{Fore.RESET}\n\n')
    return { 'country': 'Sweden', 'text' : '<p>There should be some info here.</p>' }
      


@only_central_ega
async def create_inbox(request):
    '''Inbox creation endpoint

    Not implemented yet.
    '''
    raise web.HTTPBadRequest(text=f'\n{Fore.BLACK}{Back.RED}Not implemented yet!{Back.RESET}{Fore.RESET}\n\n')

@only_central_ega
async def outgest(request):
    '''Outgestion endpoint

    Not implemented yet.
    '''
    raise web.HTTPBadRequest(text=f'\n{Fore.BLACK}{Back.RED}Not implemented yet!{Back.RESET}{Fore.RESET}\n\n')

async def status(request):
    '''Status endpoint
    '''
    file_id = request.match_info['name']
    LOG.info(f'Getting info for file_id {file_id}')
    res = await aiodb.get_info(request.app['db'], file_id)
    LOG.debug(f'RES: {res}')
    if not res:
        raise web.HTTPBadRequest(text=f'No info about "{filename}" yet...\n')
    filename, status, created_at, last_modified = res
    return web.Response(text=f'Status for {file_id}: {status}'
                        f'\n\t* Created at: {created_at}'
                        f'\n\t* Last updated: {last_modified}'
                        f'\n\t* Real file name: {filename}\n')

def process_submission(submission,
                       inbox,
                       staging_area,
                       submission_id,
                       user_id):
    '''Main function to process a submission.

    The argument is a dictionnary with information regarding one file submission.
    This function will be called upon request, and run in a separate process (a member of the ProcessPoolExecutor)
    '''

    filename         = submission['filename']
    filehash         = submission['encryptedIntegrity']['hash']
    hash_algo        = submission['encryptedIntegrity']['algorithm']

    inbox_filepath = inbox / filename
    staging_filepath = staging_area / filename

    ################# Check integrity of encrypted file
    LOG.debug(f'Verifying the {hash_algo} checksum of encrypted file: {inbox_filepath}')
    with open(inbox_filepath, 'rb') as inbox_file: # Open the file in binary mode. No encoding dance.
        if not checksum(inbox_file, filehash, hashAlgo = hash_algo):
            errmsg = f'Invalid {hash_algo} checksum for {inbox_filepath}'
            LOG.warning(errmsg)
            raise Exception(errmsg)
    LOG.debug(f'Valid {hash_algo} checksum for {inbox_filepath}')

    ################# Moving encrypted file to staging area
    LOG.debug(f'Locking the file {inbox_filepath}')
    os.chmod(inbox_filepath, mode = stat.S_IRUSR) # 400: Remove write permissions

    ################# Publish internal message for the workers
    # In the separate process
    msg = {
        'submission_id': submission_id,
        'user_id': user_id,
        'source': str(inbox_filepath),
        'target' : str(staging_filepath),
        'hash': submission['unencryptedIntegrity']['hash'],
        'hash_algo': submission['unencryptedIntegrity']['algorithm'],
    }
    _,channel = broker.get_connection()
    broker.publish(channel, json.dumps(msg), routing_to=CONF.get('message.broker','routing_todo'))
    LOG.debug('Message sent to broker')


@only_central_ega
async def ingest(request):
    '''Ingestion endpoint

    When a request is received, the POST data is parsed by `parse_data`,
    and provides information about the list of files to ingest

    The data is of the form:
    * submission id
    * user id
    * a list of files

    Each file is of the form:
    * filename
    * encrypted hash information (with both the hash value and the hash algorithm)
    * unencrypted hash information (with both the hash value and the hash algorithm)

    The hash algorithm we support are MD5 and SHA256, for the moment.

    We use a StreamResponse to send, stepwise, information about each file as they're processed.
    '''
    #assert( request[method == 'POST' )

    data = parse_data(await request.read())

    if not data:
        raise web.HTTPBadRequest(text='ERROR with POST data\n')

    response = web.StreamResponse(status=200,
                                  reason='OK',
                                  headers={'Content-Type': 'text/html'})
    await response.prepare(request)

    response.write(b'Preparing for Ingestion\n')
    await response.drain()

    submission_id = data['submissionId']
    user_id       = data['userId']

    inbox = get_inbox(user_id)
    LOG.info(f"Inbox area: {inbox}")

    staging_area = get_staging_area(submission_id, create=True)
    LOG.info(f"Staging area: {staging_area}")

    await aiodb.insert_submission(request.app['db'],
                                  submission_id = submission_id,
                                  user_id = user_id)

    # Creating a listing of the tasks to run.
    loop = request.app.loop
    success = 0
    total = len(data['files'])
    width = len(str(total))
    tasks = {} # (task -> file_id * str) mapping
    done = asyncio.Queue()

    for submission in data['files']:
        LOG.info(f"Submitting {submission['filename']}")
        file_id = await aiodb.insert_file(request.app['db'],
                                          filename  = submission['filename'],
                                          filehash  = submission['encryptedIntegrity']['hash'],
                                          hash_algo = submission['encryptedIntegrity']['algorithm'],
                                          submission_id = submission_id)
        LOG.debug(f'Created id {file_id} for {submission["filename"]}')
        task = asyncio.ensure_future(
            loop.run_in_executor(None, process_submission,
                                 submission,
                                 inbox,
                                 staging_area,
                                 submission_id,
                                 user_id) # default executor, set to ProcessPoolExecutor in main()
        ) # That will start running the task
        task.add_done_callback(lambda f: done.put_nowait(f))
        tasks[task] = (file_id, submission['filename'])

    # Running the tasks and getting the results as they arrive.
    for n in range(1,total+1):

        task = await done.get()
        file_id,filename = tasks[task]
        try:
            task.result() # May raise the exception caught in the separate process
            res = f'[{n:{width}}/{total:{width}}] {filename} {Fore.GREEN}✓{Fore.RESET}\n'
            success += 1 # no race here
            LOG.info('Success!')
            await aiodb.update_status(request.app['db'], file_id, status = db_status.In_Progress)

        except Exception as e:
            errmsg = f'Task in separate process raised {e!r}'
            LOG.error(errmsg)
            os.chmod(inbox / filename, mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP) # Permission 660
            res = f'[{n:{width}}/{total:{width}}] {filename} {Fore.RED}x{Fore.RESET}\n'
            await aiodb.set_error(request.app['db'], file_id, errmsg)
            

        # Send the result to the responde as they arrive
        await response.write(res.encode())
        await response.drain()

    assert( done.empty() )

    r = f'Ingested {success} files (out of {total} files)\n'
    await response.write(r.encode())
    await response.write_eof()
    return response

async def init(app):
    '''Initialization running before the loop.run_forever'''
    try:
        app['db'] = await aiodb.create_engine(loop=app.loop,
                                              user=CONF.get('db','username'),
                                              password=CONF.get('db','password'),
                                              database=CONF.get('db','dbname'),
                                              host=CONF.get('db','host'),
                                              port=CONF.getint('db','port'))

        LOG.info('DB Engine created')

    except Exception as e:
        print('Connection error to the Postgres database\n',str(e))
        app.loop.call_soon(app.loop.stop)
        app.loop.call_soon(app.loop.close)
        sys.exit(2)

async def shutdown(app):
    '''Function run after a KeyboardInterrupt. After that: cleanup'''
    LOG.info('Shutting down the database engine')
    app['db'].close()
    await app['db'].wait_closed()

async def cleanup(app):
    '''Function run after a KeyboardInterrupt. Right after, the loop is closed'''
    LOG.info('Cancelling all pending tasks')
    for task in asyncio.Task.all_tasks():
        task.cancel()

# async def swagger_json(request):
#     return web.json_response(
#         request.app["_swagger_config"],
#         headers={ "X-Custom-Server-Header": "Custom data",})

def main(args=None):

    if not args:
        args = sys.argv[1:]

    CONF.setup(args) # re-conf

    loop = asyncio.get_event_loop()
    server = web.Application(loop=loop)

    # Where the templates are
    template_loader = jinja2.FileSystemLoader(CONF.get('ingestion','templates',fallback=Path(__file__).parent / 'templates'))
    aiohttp_jinja2.setup(server, loader=template_loader)

    # Registering the routes
    LOG.info('Registering routes')
    server.router.add_get( '/'             , index        , name='root'       )
    server.router.add_post('/ingest'       , ingest       , name='ingestion'  )
    server.router.add_get( '/create-inbox' , create_inbox , name='inbox'      )
    server.router.add_get( '/status/{name}', status       , name='status'     )
    server.router.add_post('/outgest'      , outgest      , name='outgestion' )

    # # Swagger endpoint: /swagger.json
    # LOG.info('Preparing for Swagger')
    # swaggerify(server)
    # cors = aiohttp_cors.setup(server) # Must enable CORS
    # for route in server.router.routes(): # I don't bother and enable CORS for all routes
    #     cors.add(route, {
    #         CONF.get('swagger','url') : aiohttp_cors.ResourceOptions(
    #             allow_credentials=True,
    #             expose_headers=("X-Custom-Server-Header",),
    #             allow_headers=("X-Requested-With", "Content-Type"),
    #             max_age=3600,
    #         )
    #     })

    # Registering some initialization and cleanup routines
    LOG.info('Setting up callbacks')
    server.on_startup.append(init)
    server.on_shutdown.append(shutdown)
    server.on_cleanup.append(cleanup)

    # And ...... cue music!
    LOG.info('Starting the real deal')
    with ProcessPoolExecutor(max_workers=None) as executor: # max_workers=None number of processors on the machine
        loop.set_default_executor(executor)
        web.run_app(server,
                    host=CONF.get('ingestion','host'),
                    port=CONF.getint('ingestion','port'),
                    shutdown_timeout=0,
        )
        # https://github.com/aio-libs/aiohttp/blob/master/aiohttp/web.py
        # run_app already catches the KeyboardInterrupt and calls loop.close() at the end

        # LOG.info('Shutting down the executor')
        # executor.shutdown(wait=True)
        # # Done on exit of the with statement
        # # https://github.com/python/cpython/blob/master/Lib/concurrent/futures/_base.py#L580-L582

    LOG.info('Exiting the Ingestion server')

if __name__ == '__main__':
    main()
