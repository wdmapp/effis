#!/usr/bin/env python3

import effis.runtime
import effis.composition


if __name__ == "__main__":

    SubWorkflow = effis.runtime.SubWorkflow(
        Name="SubRun",
    )
    SubWorkflow.Subdirs = False

    runner = effis.composition.Application.DetectRunnerInfo()
    """
    if runner.__class__.__name__ == "jsrun":
        runner = effis.composition.runner.srun2jsrun()
    """

    date = SubWorkflow.Application(cmd="date", LogFile="date.log", Runner=runner, Ranks=2)

    '''
    if date.Runner.__class__.__name__ == "jsrun":
        date.nrs = 2
        date.RsPerNode = 2
        date.RanksPerRs = 1
        date.CoresPerRs = 1
    else:
        date.Ranks = 2
    '''

    ls = SubWorkflow.Application(cmd="ls", DependsOn=date, Runner=runner, Ranks=1)

    '''
    if ls.Runner.__class__.__name__ == "jsrun":
        ls.nrs = 1
        ls.RsPerNode = 1
        ls.RanksPerRs = 1
        ls.CoresPerRs = 1
    else:
        ls.Ranks = 1
    '''

    
    #SubWorkflow.Create()

    tid = SubWorkflow.Submit(wait=False)

    finished = []
    while len(finished) < len(SubWorkflow.Applications):
        for app in SubWorkflow.Applications:
            if 'procid' not in app.__dir__():
                continue
            elif (app.procid.poll() != None) and (app.procid not in finished):
                finished += [app.procid]

    while tid.is_alive():
        pass
