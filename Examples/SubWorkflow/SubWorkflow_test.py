import SubWorkflow

class SimpleArgs:
    batchtype = "local"
    outdir = "SimpleTest"


def test_Run():
    print("test_Run()")
    args = SimpleArgs()
    SubWorkflow.Run(args)
