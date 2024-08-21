import effis.composition
import argparse
import os
import dill as pickle


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Path to directory", type=str)
    parser.add_argument("--rerun", help="Force rerun (if already finished before)", action="store_true")
    args = parser.parse_args()

    filename = os.path.join(args.directory, "workflow.pickle")
    if not os.path.exists(filename):
        raise ValueError("No workflow description found in {0}".format(args.directory))

    with open(filename, 'rb') as handle:
        workflow = pickle.load(handle)

    workflow.Submit(rerun=args.rerun)
