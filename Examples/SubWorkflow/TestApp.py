#!/usr/bin/env python3

import effis.composition
import logging


if __name__ == "__main__":

    effis.composition.EffisLogger.SetLevel(logging.WARNING)

    SubWorkflow = effis.composition.SubWorkflow(
        Name="SubRun",
    )
    SubWorkflow.Subdirs = False

    ls = SubWorkflow.Application(cmd="ls", Ranks=1)
    date = SubWorkflow.Application(cmd="date", Ranks=2)
    
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
