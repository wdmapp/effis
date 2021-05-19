#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import globus_sdk
import argparse
import yaml
import sys
import os
import re
import time
import logging


def ReadYAML(yamlfile):
    with open(yamlfile, 'r') as ystream:
        backup = yaml.load(ystream, Loader=yaml.FullLoader)
    if 'keeplinks' not in backup:
        backup['keeplinks'] = False

    return backup


def AuthorizeTransferClient(clientid):
    """
    To do useful things, Globus API requires web authorization.
    """
    
    client = globus_sdk.NativeAppAuthClient(clientid)
    client.oauth2_start_flow(refresh_tokens=True)
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


def ActivateEndpoint(tc, backup, idhash, idname, title, out=None):
    """
    Endpoints are also activated online.
    To identify endpoints, users can provide either the UUID or select a result from a name search.
    """
    if out is None:
        PrintFunction = print
    else:
        PrintFunction = out

    if idhash not in backup:
        res = tc.endpoint_search(backup[idname])
        results = []
        for result in res:
            results += [result]
        if len(results) == 0:
            raise ValueError("{0}='{1}' did not match any results in Globus search".format(idname, backup[idname]))
        PrintFunction("Search results for {0}='{1}':".format(idname, backup[idname]))
        for i, result in enumerate(results):
            PrintFunction("{0}: display_name='{1}', id='{2}'".format(i, result['display_name'], result['id']))
        PrintFunction('Please enter integer selection: ', end="")
        selection = input().strip()
        try:
            selection = int(selection)
        except:
            raise ValueError("Did not enter an integer")
        else:
            if (selection < 0) or (selection >= len(results)):
                raise ValueError("i={0} not in range  0 <= i <= {1}".format(selection, len(results)-1))
        backup[idhash] = results[selection]['id']

    # The function doesn't work correctly without if_expires
    r = tc.endpoint_autoactivate(backup[idhash], if_expires_in=60)
    url = "https://app.globus.org/file-manager?origin_id={0}".format(backup[idhash])
    first = True
    while (r['code'] == "AutoActivationFailed"):
        if first:
            PrintFunction("{0} requires manual activation, please open the following URL in a browser to activate the endpoint:".format(title) + "\n" + url)
            PrintFunction("Submission will continue upon activation.")
            first = False
        time.sleep(5)
        r = tc.endpoint_autoactivate(backup[idhash], if_expires_in=60)
        """
        PrintFunction("{0} requires manual activation, please open the following URL in a browser to activate the endpoint:".format(title) + "\n" + url)
        PrintFunction("Press ENTER after activating the endpoint:", end="")
        input()
        r = tc.endpoint_autoactivate(backup[idhash], if_expires_in=60)
        """

    if (r["expire_time"] is not None) and (out is None):
        PrintFunction("{0} authorization expires at {1}. You may need to reactivate it at {2}".format(title, r["expire_time"], url))


def FindCopies(endpoint, directory, copypaths=[], searchadd=None, keeplinks=False):
    """
    Recursively look for paths that match the search pattern.
    The search is relative to the top directory of the run.
    Results are returned as absolute paths.
    """

    if 'search' not in endpoint:
        if 'pattern' in endpoint:
            pattern = endpoint['pattern']
        else:
            pattern = ".*"
        endpoint['search'] = re.compile(pattern)

    paths = os.listdir(directory)
    for path in paths:
        searchpath = path
        if searchadd is not None:
            searchpath = os.path.join(searchadd, path)
        match = endpoint['search'].search(searchpath)
        fullpath = os.path.join(os.path.abspath(directory), path)

        if (not keeplinks) and (path == ".cheetah"):
            continue
        elif (match is None) and os.path.isdir(fullpath):
            if searchadd is None:
                copypaths = FindCopies(endpoint, fullpath, copypaths=copypaths, searchadd=path, keeplinks=keeplinks)
            else:
                copypaths = FindCopies(endpoint, fullpath, copypaths=copypaths, searchadd=os.path.join(searchadd, path), keeplinks=keeplinks)
        elif match is not None:
            copypaths += [fullpath]

        # Always include the links EFFIS makes to the code subdiretories
        if keeplinks and (searchadd is None) and (fullpath not in copypaths) and os.path.isdir(fullpath) and os.path.islink(fullpath) and (os.path.realpath(fullpath).find(".cheetah") != -1):
            copypaths += [fullpath]

    return copypaths


def makepath(destdir, matchname, name, endpoint, tc):
    """
    Make a directory on a Globus endpoint if it doesn't exist
    """

    found = False
    results = tc.operation_ls(endpoint['id'], path=destdir)
    for result in results:
        if result['name'] == matchname:
            found = True
            break
    if not found:
        dest = os.path.join(destdir, matchname)
        logging.info("Endpoint {1}: mkdir {0}".format(dest, name))
        tc.operation_mkdir(endpoint['id'], path=dest)


def MakePath(path, topdir, desttop, name, endpoint, tc):
    """
    Recursively make sure directories exist for transfers.
    """

    relpath = os.path.relpath(path, start=topdir)
    dirs = relpath.split('/')
    cdir = desttop
    while len(dirs) > 1:
        makepath(cdir, dirs[0], name, endpoint, tc)
        cdir = os.path.join(cdir, dirs[0])
        dirs = dirs[1:]
    return os.path.join(cdir, dirs[0])


if __name__ == "__main__":

    # args.yamlfile is written by effis-compose.py: from the "backup" section of the config file
    parser = argparse.ArgumentParser()
    parser.add_argument("yamlfile", help="Settings file")
    args = parser.parse_args()

    # Read the setup
    backup = ReadYAML(args.yamlfile)

    # The client ID is registration for apps that use Globus; here, one made for EFFIS
    clientid = "fbe7f352-d1f0-45e5-9fb8-889dec66ec8f"
    tc = AuthorizeTransferClient(clientid)

    # Make sure endpoints are authorized.
    # Reauthorization may be needed by the time the transfer actually occurs, depending on run/queue time.
    ActivateEndpoint(tc, backup, 'local-id', 'local-name', "Local host")
    for name in backup['endpoints']:
        ActivateEndpoint(tc, backup['endpoints'][name], 'id', 'name', "Endpoint {0}".format(name))

    # Tell the main submit program that the authorization setup is ready
    print("STATUS=READY", file=sys.stderr)
    sys.stderr.flush()
    sys.stdout.flush()

    # Paths
    setupdir = os.path.dirname(os.path.abspath(args.yamlfile))
    topdir = os.path.dirname(setupdir)
    topname = os.path.basename(topdir)
    donefile = os.path.join(topdir, ".backup.ready")
    logfile = os.path.join(os.path.join(setupdir, 'globus.log'))

    # Open a log file, since this is running in the background
    logging.basicConfig(filename=logfile, level=logging.INFO)

    # Wait until the run is over and the data is ready to move
    logging.info("Waiting for signal to begin data backup")
    while not os.path.exists(donefile):
        time.sleep(1)
    logging.info("Got signal to begin data backup. Continuing...")

    try:
        # Match copy patterns and schedule copies to endpoints
        for name in backup['endpoints']:
            endpoint = backup['endpoints'][name]
            copypaths = FindCopies(endpoint, topdir, keeplinks=backup['keeplinks'])

            logging.info("\nEndpoint {0} paths to copy:".format(name))
            for copypath in copypaths:
                logging.info("\t{0}".format(copypath))

            desttop = topname
            if 'destination' in endpoint:
                desttop = os.path.join(endpoint['destination'], topname)

            # Make sure endpoints are authorized.
            ActivateEndpoint(tc, backup, 'local-id', 'local-name', "Local host", out=logging.info)
            ActivateEndpoint(tc, backup['endpoints'][name], 'id', 'name', "Endpoint {0}".format(name), out=logging.info)

            # Make the top directory at the transfer endpoint if it does not exist
            # I'm not sure what the behavior should be if it exist -- not sure and overwrite is wanted
            makepath(os.path.dirname(desttop), topname, name, endpoint, tc)

            # Initialize Globus transfer engine to transfer endpoint
            transfer = globus_sdk.TransferData(tc, backup['local-id'], endpoint['id'], label=name)

            # Iteratively do the copies
            for copypath in copypaths:
                path = MakePath(copypath, topdir, desttop, name, endpoint, tc)
                if backup['keeplinks'] and os.path.islink(copypath) and (os.path.abspath(os.path.realpath(copypath)).find(topname) != -1):
                    logging.info("Adding sylink item {0} to {1}".format(copypath, path))
                    transfer.add_symlink_item(copypath, path)
                else:
                    logging.info("Adding ordinary item {0} to {1}".format(copypath, path))
                    recursive = False
                    if os.path.isdir(copypath):
                        recursive = True
                    transfer.add_item(copypath, path, recursive=recursive)
               
            logging.info("Submitting Globus transfer for endpoint {0}".format(name))
            transfer_result = tc.submit_transfer(transfer)
            logging.info("Transfer result: \n{0}".format(transfer_result))
    except:
        logging.exception("Globus error")

