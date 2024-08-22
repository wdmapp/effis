import socket
import json
import argparse
import sys
import os
import time

import logging
logger = logging.getLogger(__name__)

import globus_sdk
from globus_sdk.scopes import TransferScopes
import globus


def AutoActivate(tc, idhash, label):
    r = tc.endpoint_autoactivate(idhash, if_expires_in=3600)
    url = "https://app.globus.org/file-manager?origin_id={0}".format(idhash)
    first = True
    while (r['code'] == "AutoActivationFailed"):
        if first:
            print("{0} endpoint requires manual activation, please open the following URL in a browser to activate the endpoint:".format(label) + "\n" + url)
            print("Submission will continue upon activation.")
            first = False
        time.sleep(5)
        r = tc.endpoint_autoactivate(idhash, if_expires_in=3600)


def GetTransferClient(scopes=[TransferScopes.all]):

    # Set up for EFFIS
    clientid = "fbe7f352-d1f0-45e5-9fb8-889dec66ec8f"

    client = globus_sdk.NativeAppAuthClient(clientid)
    client.oauth2_start_flow(refresh_tokens=True, requested_scopes=scopes)
    authorize_url = client.oauth2_get_authorize_url()
    print('Please go to this URL and login: {0}'.format(authorize_url))
    print('Please enter the code you get after login here: ', end="")
    auth_code = input().strip()
    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    globus_transfer_data = token_response.by_resource_server['transfer.api.globus.org']
    access_token = globus_transfer_data['access_token']
    refresh_token = globus_transfer_data['refresh_token']
    expires_at = globus_transfer_data['expires_at_seconds']
    authorizer = globus_sdk.RefreshTokenAuthorizer(refresh_token, client, access_token=access_token, expires_at=expires_at)
    tc = globus_sdk.TransferClient(authorizer=authorizer)

    return tc


def MakeDirs(endpoint, fullpath):
    dirname, lastname = os.path.split(fullpath)
    try:
        logger.info("{0} -- ls: {1}".format(endpoint, dirname))
        results = tc.operation_ls(endpoint, path=dirname)
    except globus_sdk.TransferAPIError as err:
        if err.args[3] == 404:
            MakeDirs(endpoint, dirname)
        else:
            raise
    except:
        raise

    else:
        logger.info("{0} -- mkdir: {1}".format(endpoint, fullpath))
        tc.operation_mkdir(endpoint, path=fullpath)



if __name__ == "__main__":
        
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonfile", help="Path to json file")
    parser.add_argument("--checkdest", help="Check if destination directory is accessible", action="store_true")
    args = parser.parse_args()

    # Open a log file, since this will be running in the background
    logfile = os.path.join(os.path.dirname(os.path.abspath(args.jsonfile)), 'globus.log')

    # This works because logger's are hierarchical and messages get forwarded up
    logging.basicConfig(filename=logfile, level=logging.INFO)

    """
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(logfile, mode="a", encoding="utf-8")
    logger.addHandler(file_handler)

    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(file_handler)
    """


    print("\n" + "Setting up Globus transfer client...")
    with open(args.jsonfile) as infile:
        config = json.load(infile)


    endpoints = []
    for endpoint in config['endpoints']:
        endpoints += [config['endpoints'][endpoint]['id']]
    client = globus.AuthorizedTranserClient(config['source'], *endpoints, TokensFile=os.path.join(os.environ["HOME"], ".effis-globustokens"))
    tc = client.TransferClient

    if args.checkdest:
        for endpoint in config['endpoints']:
            for paths in config['endpoints'][endpoint]['paths']:
                done = False
                while not done:
                    try:
                        results = tc.operation_ls(config['endpoints'][endpoint]['id'], path=paths['outpath'])
                    except globus_sdk.TransferAPIError as err:
                        if (err.args[3] == 404):
                            MakeDirs(config['endpoints'][endpoint]['id'], paths['outpath'])
                        else:
                            raise
                    except:
                        raise
                    else:
                        done = True


    """
    scopes = [TransferScopes.all]
    tc = GetTransferClient(scopes=scopes)

    AutoActivate(tc, config['source'], "Host")
    for endpoint in config['endpoints']:
        AutoActivate(tc, config['endpoints'][endpoint]['id'], endpoint)

        for paths in config['endpoints'][endpoint]['paths']:
            done = False

            while not done:
                try:
                    results = tc.operation_ls(config['endpoints'][endpoint]['id'], path=paths['outpath'])
                except globus_sdk.TransferAPIError as err:
                    if err.args[3] == 403:
                        scopes += err.info.consent_required.required_scopes
                        print("Need additional consents")
                        tc = GetTransferClient(scopes=scopes)
                    elif (err.args[3] == 404) and args.checkdest:
                        MakeDirs(config['endpoints'][endpoint]['id'], paths['outpath'])
                    else:
                        raise
                except:
                    raise
                else:
                    done = True
    """

    print("Got AuthorizedTransferClient\n")
    print("STATUS=READY", file=sys.stderr)
    sys.stderr.flush()
    sys.stdout.flush()

    try:
        logger.info("Waiting for signal to begin data backup")
        while not os.path.exists(config['readyfile']):
            time.sleep(3)
        logger.info("Got signal to begin data backup. Continuing...")

        for endpoint in config['endpoints']:

            label = "host={0}; destination={1}".format(config['source'], config['endpoints'][endpoint]['id'])
            logger.info(label)
            transfer = globus_sdk.TransferData(tc, config['source'], config['endpoints'][endpoint]['id'], label=label)

            for paths in config['endpoints'][endpoint]['paths']:

                # Directories use recursive setting in Globus; for now don't try to handle links
                recursive = False
                if os.path.isdir(paths['inpath']):
                    recursive = True

                # Remove trailing slashes for comparision clarity
                paths['inpath'] = paths['inpath'].rstrip('/')
                paths['outpath'] = paths['outpath'].rstrip('/')
                fname = os.path.basename(paths['inpath'])
                oname = os.path.basename(paths['outpath'])

                if (oname != fname) and (paths['rename'] is not None):
                    paths['outpath'] = os.path.join(paths['outpath'], paths['rename'])
                elif (oname != fname):
                    paths['outpath'] = os.path.join(paths['outpath'], fname)
                    
                logger.info("transfer item: {0} --> {1}  [recursive={2}".format(paths['inpath'], paths['outpath'], recursive))
                transfer.add_item(paths['inpath'], paths['outpath'], recursive=recursive)


            logger.info("Submitting Globus transfer for: {0}".format(label))
            transfer_result = tc.submit_transfer(transfer)
            logger.info("Transfer result: \n{0}".format(transfer_result))

    except Exception as e:
        logger.exception(e)

