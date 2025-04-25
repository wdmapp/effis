#!/usr/bin/env python3

import argparse
import effis.runtime
import effis.composition


if __name__ == "__main__":

    fullparser = argparse.ArgumentParser()
    fullparser.add_argument("-l", "--local", help="Use local run", action="store_true")
    args = fullparser.parse_args()

    runner = None
    appsetup = {}

    if not args.local:
        runner = effis.composition.Application.DetectRunnerInfo()
        appsetup['Ranks'] = 2
        appsetup['RanksPerNode'] = 2
        appsetup['CoresPerRank'] = 2


    SubWorkflow = effis.runtime.SubWorkflow(
        Name="SubRun",
        Subdirs=False,
    )

    '''
    # mpiexec-hydra doesn't have a cores per rank setting
    if runner.__class__.__name__ == "mpiexec_hydra":
        del appsetup['CoresPerRank']
    '''

    date = SubWorkflow.Application(
        cmd="date",
        Runner=runner,
        LogFile="date.log",
        **appsetup,
    )

    for key in appsetup:
        appsetup[key] = 1

    ls = SubWorkflow.Application(
        cmd="ls",
        Runner=runner,
        DependsOn=date,
        **appsetup,
    )


    tid = SubWorkflow.Submit(wait=False)
    tid.join()

    """
    finished = []
    while len(finished) < len(SubWorkflow.Applications):
        for app in SubWorkflow.Applications:
            if 'procid' not in app.__dir__():
                continue
            elif (app.procid.poll() != None) and (app.procid not in finished):
                finished += [app.procid]

    while tid.is_alive():
        pass
    """

