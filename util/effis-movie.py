#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals
import subprocess
import argparse
import os
import re
import shutil


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Directory to job to run")
    args = parser.parse_args()

    pattern = re.compile("^\.(.*)\.movie\.txt$")
    subdirs = os.listdir(args.directory)
    for subdir in subdirs:
        path = os.path.join(args.directory, subdir)
        if os.path.isdir(path):
            subfiles = os.listdir(path)
            for subfile in subfiles:
                match = pattern.search(subfile)
                if match is not None:
                    subfile = os.path.join(args.directory, subdir, subfile)
                    with open(subfile) as infile:
                        txt = infile.read()
                    images = txt.strip().split()
                    if not os.path.exists(".tmp"):
                        os.makedirs(".tmp")
                    for i, image in enumerate(images):
                        base, ext = os.path.splitext(image)
                        linkname = os.path.join(".tmp", "{0}-{1}.{2}".format(match.group(1), i, ext))
                        os.symlink(image, linkname)
                        
                    #outname = "{0}.mp4".format(match.group(1))
                    #args = ['ffmpeg', '-i',  os.path.join(".tmp", "{0}-%d.{1}".format(match.group(1), ext)), "-c:v", "libx264", "-crf", "0", outname]

                    #outname = "{0}.mp4".format(match.group(1))
                    #args = ['ffmpeg', '-i',  os.path.join(".tmp", "{0}-%d.{1}".format(match.group(1), ext)), "-c:v", "libx265", "-x265-params", "lossless=1", outname]

                    #outname = "{0}.webm".format(match.group(1))
                    #args = ['ffmpeg', '-i',  os.path.join(".tmp", "{0}-%d.{1}".format(match.group(1), ext)), "-c:v", "libvpx-vp9", "-lossless", "1", outname]

                    #outname = "{0}.mkv".format(match.group(1))
                    #args = ['ffmpeg', '-i',  os.path.join(".tmp", "{0}-%d.{1}".format(match.group(1), ext)), "-c:v", "copy", outname]
                    
                    #outname = "{0}.avi".format(match.group(1))
                    #args = ['ffmpeg', '-i',  os.path.join(".tmp", "{0}-%d.{1}".format(match.group(1), ext)), "-c:v", "huffyuv", outname]

                    outname = os.path.join(args.directory, subdir, "{0}.avi".format(match.group(1)))
                    ffmpeg_args = ['ffmpeg', '-i',  os.path.join(".tmp", "{0}-%d.{1}".format(match.group(1), ext)), "-c:v", "ffv1", outname]

                    print(ffmpeg_args)
                    subprocess.call(ffmpeg_args)
                    shutil.rmtree(".tmp")
