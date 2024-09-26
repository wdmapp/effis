#!/usr/bin/env python3

import effis.runtime


if __name__ == "__main__":

    SubWorkflow = effis.runtime.SubWorkflow(
        Name="SubRun",
    )
    SubWorkflow.Subdirs = False

    date = SubWorkflow.Application(cmd="date", LogFile="date.log")
    if date.Runner.__class__.__name__ == "jsrun":
        date.nrs = 2
        date.RsPerNode = 2
        date.RanksPerRs = 1
        date.CoresPerRs = 1
    else:
        date.Ranks = 2

    ls = SubWorkflow.Application(cmd="ls", DependsOn=date)
    if ls.Runner.__class__.__name__ == "jsrun":
        ls.nrs = 1
        ls.RsPerNode = 1
        ls.RanksPerRs = 1
        ls.CoresPerRs = 1
    else:
        ls.Ranks = 1

    
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
