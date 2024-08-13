#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function, unicode_literals

import yaml
import numpy as np
import subprocess
import os
import sys
import json
import re
import datetime

import adios2

import globus_sdk
from globus_sdk.scopes import TransferScopes

import socket
import time
import shutil


class HostRemote:

    def __init__(self, hostid, destid, tc):
        self.hostid = hostid
        self.destid = destid
        self.tc = tc
        
        #self.httpdir = "/global/cfs/projectdirs/m499/esimmon/watch/esuchyta-test/"
        self.httpdir = "/global/cfs/cdirs/m499/esimmon/watch/shots"

        #self.tmpdir = "/ccs/home/esuchyta/tmp"
        self.tmpdir = os.path.join(os.getcwd(), datetime.datetime.now().strftime('%Y-%m-%dT%H.%M.%S.%f'))
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)


    def exists(self, path):
        found = False
        entries = self.tc.operation_ls(self.destid, path=os.path.dirname(path))
        for entry in entries:
            if entry["name"] == os.path.basename(path):
                found = True
                break
        return found


    def mkdir(self, path):
        if not self.exists(path):
            self.tc.operation_mkdir(self.destid, path=path)


    def WriteRemote(self, jdict, filename, wait=True, submit=True, transfer=None, subdir="", asdir=False):
        jdir = os.path.join(self.tmpdir, subdir)
        if not os.path.exists(jdir):
            os.makedirs(jdir)
        jfile = os.path.join(jdir, os.path.basename(filename))
        with open(jfile, 'w') as outfile:
            json.dump(jdict, outfile, indent=self.indent)

        if transfer is None:
            transfer = globus_sdk.TransferData(self.tc, self.hostid, self.destid, label=os.path.basename(filename), notify_on_succeeded=False)

        if asdir:
            transfer.add_item(jdir, os.path.dirname(filename), recursive=True)
        else:
            transfer.add_item(jfile, filename)

        if submit:
            result = self.tc.submit_transfer(transfer)
            if wait:
                while not self.tc.task_wait(result["task_id"], timeout=60, polling_interval=2):
                    pass
            return result["task_id"]
        else:
            return transfer


    def WriteTimeFile(self, timedict, **kwargs):
        self.WriteRemote(timedict, self.timefile, **kwargs)


    def WriteVarFile(self, vardict, **kwargs):
        taskid = self.WriteRemote(vardict, self.varfile, subdir=os.path.basename(os.path.dirname(self.varfile)), asdir=True, **kwargs)
        return taskid


    def IndexJSON(self, config, indent=4):
        outdict = {}
        for name in ['shot_name', 'run_name', 'username', 'machine_name']:
            outdict[name] = config['login'][name]
        outdict['date'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S+%f')

        if 'globus-period' in config['login']:
            self.period = config['login']['globus-period']
        else:
            self.period = 20

        if 'finishonly' in config['login']:
            self.finishonly = True
        else:
            self.finishonly = False

        #httpdir = config['login']['http']
        self.indexfile = os.path.join(self.httpdir, 'index.json')
        shotdir = os.path.join(self.httpdir, outdict['shot_name'])
        rundir = os.path.join(shotdir, outdict['run_name'])
        self.timefile = os.path.join(rundir, "time.json")
        timedict = {"current": 0, "complete": False, "started": False}


        self.indent = indent
        self.mkdir(shotdir)
        self.mkdir(rundir)
        if not self.exists(self.timefile):
            self.WriteTimeFile(timedict)

        self.ifile = os.path.join(self.tmpdir, os.path.basename(self.indexfile))
        if not self.exists(self.indexfile):
            outlist = []
        else:
            transfer = globus_sdk.TransferData(self.tc, self.destid, self.hostid, label="Index file", notify_on_succeeded=False)
            transfer.add_item(self.indexfile, self.ifile)
            result = self.tc.submit_transfer(transfer)
            while not self.tc.task_wait(result["task_id"], timeout=60, polling_interval=2):
                pass
            with open(self.ifile, 'r') as ystream:
                outlist = yaml.load(ystream, Loader=yaml.FullLoader)
        outlist += [outdict]
        with open(self.ifile, 'w') as outfile:
            json.dump(outlist, outfile, indent=self.indent)

        if not self.finishonly:
            transfer = globus_sdk.TransferData(self.tc, self.hostid, self.destid, label="Top index file", notify_on_succeeded=False)
            transfer.add_item(self.ifile, self.indexfile)
            result = self.tc.submit_transfer(transfer)
            while not self.tc.task_wait(result["task_id"], timeout=60, polling_interval=2):
                pass

        return timedict


    def FinishOnly(self):
        if self.finishonly:
            transfer = globus_sdk.TransferData(self.tc, self.hostid, self.destid, label="Top index file", notify_on_succeeded=False)
            transfer.add_item(self.ifile, self.indexfile)
            result = self.tc.submit_transfer(transfer)
            while not self.tc.task_wait(result["task_id"], timeout=60, polling_interval=2):
                pass



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




if __name__ == "__main__":

	############################################################################################################

    scopes = [TransferScopes.all]
    tc = GetTransferClient(scopes=scopes)

    """
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
    """

    nerscdtn = "9d6d994a-6d04-11e5-ba46-22000b92c6ec"
    #host = socket.getfqdn()
    host = socket.getaddrinfo(socket.gethostname(), 0, flags=socket.AI_CANONNAME)[0][3]
    if host.find("olcf.ornl.gov") != -1:
        hostid = "36d521b3-c182-4071-b7d5-91db5d380d42"
    elif host.find("perlmutter") != -1:
        hostid = "6bdc7956-fc0f-4ad2-989c-7aa5ee643a79"
    else:
        print('Could not automatically find host endpoint identity. Please enter the id hash to use: ', end="")
        hostid = input().strip()

    AutoActivate(tc, hostid, "Host")
    AutoActivate(tc, nerscdtn, "Destination")
    connection = HostRemote(hostid, nerscdtn, tc)

	############################################################################################################

    indent = 4
    yamlfile = "step-info.yaml"
    with open(yamlfile, 'r') as ystream:
        config = yaml.load(ystream, Loader=yaml.FullLoader)

    try:
        timedict = connection.IndexJSON(config, indent=indent)
    except globus_sdk.TransferAPIError as err:
        scopes += err.info.consent_required.required_scopes
        tc = GetTransferClient(scopes=scopes)
    del config['login']

    adios = adios2.Adios()


    setup = {}
    setup['done'] = 0
    setup['size'] = len(list(config.keys()))
    setup['LastStep'] = -1
    for name in config.keys():
        setup[name] = {}
        setup[name]['io'] = adios.declare_io(name)
        setup[name]['io'].set_parameter('OpenTimeoutSecs', '3600')

        setup[name]['opened'] = False
        setup[name]['LastStep'] = np.array([-1], dtype=np.int64)
        setup[name]['done'] = False


    transfer = None
    ptime = datetime.datetime.now()


    while True:

        if setup['done'] == setup['size']:
            timedict['complete'] = True
            #connection.WriteTimeFile(timedict)
            t1 = datetime.datetime.now()
            connection.WriteTimeFile(timedict, wait=True, submit=True, transfer=transfer)
            t2 = datetime.datetime.now()
            finishtime = (t2 - t1).total_seconds()
            print("Finish step time: {0:.2f} s".format(finishtime))
            connection.FinishOnly()
            shutil.rmtree(connection.tmpdir)
            break

        for name in config.keys():

            if setup[name]['done']:
                continue

            if not setup[name]['opened']:
                # Need to have a filename here
                setup[name]['engine'] = adios2.Stream(setup[name]['io'], config[name]['stepfile'], "r")
                setup[name]['opened'] = True

            ReadStatus = setup[name]['engine'].begin_step(timeout=0.1)

            if ReadStatus == adios2.bindings.StepStatus.NotReady:
                continue
            elif ReadStatus != adios2.bindings.StepStatus.OK:
                print("Found last in ", name); sys.stdout.flush()
                setup[name]['done'] = True
                setup['done'] += 1
                setup[name]['engine'].close()
                continue

            varid = setup[name]['io'].inquire_variable("Step")
            setup[name]['LastStep'] = setup[name]['engine'].read(varid)
            setup[name]['engine'].end_step()


        check = 0
        minfound = None
        for name in config.keys():
            if (setup[name]['LastStep'] <= setup['LastStep']) and (not setup[name]['done']):
                break
            if (minfound is None) or (setup[name]['LastStep'] < minfound):
                minfound = setup[name]['LastStep']
            check += 1


        if check == setup['size']:

            for i in range(setup['LastStep']+1, minfound+1):

                vardict = []
                vardir = os.path.join(os.path.dirname(connection.timefile), "{0}".format(i))
                connection.varfile = os.path.join(vardir, "variables.json")
                #connection.mkdir(vardir)

                vardir = os.path.join(connection.tmpdir, "{0}".format(i))
                if not os.path.exists(vardir):
                    os.makedirs(vardir)
                
                tarargs = []
                allfiles = []
                allgroups = []
                for name in config.keys():
                    '''
                    topdir = os.path.abspath(os.path.dirname(config[name]))
                    code, label = name.split('.', 1)
                    label = os.path.basename(config[name])[:-8]
                    middir = os.path.join(topdir, "{0}-images".format(label), str(i))
                    name = "{0}-{1}".format(code, label)
                    subdir = os.path.join(middir, name)
                    '''

                    topdir = os.path.abspath(config[name]['imagedir'])
                    middir = os.path.join(topdir, str(i))
                    subdir = os.path.join(middir, name)

                    if os.path.exists(subdir):
                        files = os.listdir(subdir)
                        tarargs += ["-C", middir, name]

                        if "plots.json" in files:
                            with open(os.path.join(subdir, "plots.json")) as jfile:
                                vardict += json.loads(jfile.read())
                        else:
                            for j in range(len(files)):
                                files[j] = os.path.join(name, files[j])
                                allgroups += [name]
                            allfiles += files

                for filename, groupname in zip(allfiles, allgroups):
                    fname = os.path.basename(filename)
                    name, ext = os.path.splitext(fname)

                    # I should make this a double underscore or something
                    try:
                        yname, xname = name.split('_vs_')
                    except:
                        pattern = "([a-zA-Z0-9]*).*"
                        comp = re.compile(pattern)
                        match = comp.search(name)
                        yname = match.group(1)

                    vardict += [{'variable_name': yname, 'image_name': filename, 'group_name': groupname}]

                t1 = datetime.datetime.now()
                #vardir = connection.tmpdir
                tarfile = os.path.join(vardir, "images.tar.gz".format(i))
                if len(tarargs) > 0:
                    subprocess.call(['tar', 'cfzh', tarfile] + tarargs)
                else:
                    if not os.path.exists("images"):
                        os.makedirs("images")
                    subprocess.call(['tar', 'cfz', tarfile, "images/"])
                t2 = datetime.datetime.now()
                tartime = (t2 - t1).total_seconds()

                t1 = datetime.datetime.now()
                transfer = connection.WriteVarFile(vardict, wait=False, submit=False, transfer=transfer)
                #varid = connection.WriteVarFile(vardict, wait=False, submit=True)
                t2 = datetime.datetime.now()
                queuetime = (t2 - t1).total_seconds()

                """
                t1 = datetime.datetime.now()
                while not connection.tc.task_wait(varid, timeout=60, polling_interval=2):
                    pass
                t2 = datetime.datetime.now()
                print("Transfer Variables File – {0:.1f} s".format((t2 - t1).total_seconds()))
                """

                transfertime = 0.0
                timedict['current'] = i
                timedict['started'] = True
                #connection.WriteTimeFile(timedict)

                newtime = datetime.datetime.now()
                timediff = (newtime - ptime).total_seconds()

                if (len(tarargs) > 0) and (timediff > connection.period):
                    #t1 = datetime.datetime.now()
                    ptime = datetime.datetime.now()
                    t1 = ptime
                    connection.WriteTimeFile(timedict, wait=True, submit=True, transfer=transfer)
                    t2 = datetime.datetime.now()
                    transfertime += (t2 - t1).total_seconds()
                    transfer = None
                    #ptime = datetime.datetime.now()

                    '''
                    print("Step integer {3} -- tar time: {0:.2f} s, queue time: {1:.2f}, transfer time: {2:.2f}".format(tartime, queuetime, transfertime, i))
                    time.sleep(60)
                    print("DONE SLEEPING")
                    '''

                print("Step integer {3} -- tar time: {0:.2f} s, queue time: {1:.2f}, transfer time: {2:.2f}".format(tartime, queuetime, transfertime, i))

            setup['LastStep'] = minfound

