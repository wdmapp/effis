#!/usr/bin/env python3

import effis.composition


if __name__ == "__main__":

    SubWorkflow = effis.composition.SubWorkflow(
        Name="SubRun",
    )
    SubWorkflow.Subdirs = False

    ls = SubWorkflow.Application(cmd="ls", Ranks=1)
    date = SubWorkflow.Application(cmd="date", Ranks=2)
    
    SubWorkflow.Create()
    SubWorkflow.Submit()
