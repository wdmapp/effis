import argparse
import os
import dill as pickle


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Path to directory", type=str)
    parser.add_argument("--sub", help="Sub-submit", action="store_true")
    parser.add_argument("-n", "--name", help="Workflow Name", required=False, default=None)
    args = parser.parse_args()

    if args.name is not None:
        filename = os.path.join(args.directory, "{0}.workflow.pickle".format(args.name))

    else:
        names = os.listdir(args.directory)
        count = 0
        for name in names:
            if name.endswith("workflow.pickle") and (not name.endswith("sub.workflow.pickle")):
                filename = name
                count += 1

        if count == 1:
            filename = os.path.join(args.directory, filename)
        elif count > 1:
            raise NameError("More than one workflow description found. Set one with --name")
        elif count == 0:
            raise NameError("No workflow description found.")


    if not os.path.exists(filename):
        raise ValueError("No workflow description found in {0}".format(args.directory))

    with open(filename, 'rb') as handle:
        workflow = pickle.load(handle)

    if args.sub:
        workflow.SubSubmit()
    else:
        workflow.Submit()
