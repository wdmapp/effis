#!/usr/bin/env python3

import time
import socket
import argparse


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--SleepTime", "-t", help="Time to sleep", type=int, default=60)
    args = parser.parse_args()

    hostname = socket.gethostname()
    print(hostname)
    
    time.sleep(args.SleepTime)