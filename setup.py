from setuptools import setup, find_namespace_packages
from setuptools.command.build_py import build_py

"""
from setuptools.command.install import install
from setuptools.command.build import build
from setuptools.command.egg_info import egg_info
from setuptools.command.dist_info import dist_info
from setuptools.command.editable_wheel import editable_wheel
"""

import site
import sys
import os
import shutil
import subprocess


class CustomInstallPy(build_py):

    def run(self):
       
        try:
            import pybind11
        except:
            raise ImportError("Could not find pybind11")
    
        cwd = os.path.dirname(os.path.abspath(__file__))
        cpp = os.path.join(cwd, "src", "effis", "cpp")
        buildname = "build"
        builddir = os.path.join(cpp, buildname)
        if os.path.exists(builddir):
            shutil.rmtree(builddir)
        os.makedirs(builddir)
       
        args  = ["cmake"]
        args += ["-DCMAKE_INSTALL_PREFIX={0}".format(cpp)]
        args += ["-DCMAKE_PREFIX_PATH={0}".format(pybind11.get_cmake_dir())]
        args += ["-DCMAKE_VERBOSE_MAKEFILE=ON"]
        args += ["-B", builddir]
        args += ["-S", cpp]
        print(" ".join(args)); sys.stdout.flush()
        subprocess.call(args)

        args  = ["cmake", "--build", builddir]
        print(" ".join(args)); sys.stdout.flush()
        #subprocess.call(args)
        p = subprocess.Popen(args)
        p.wait()
        if p.returncode != 0:
            raise Exception("CMake build failed")

        args  = ["cmake", "--install", builddir]
        print(" ".join(args)); sys.stdout.flush()
        subprocess.call(args)

        build_py.run(self)
        #print("argv2:", sys.argv); sys.stdout.flush()



if __name__ == "__main__":
    sys.path += site.getsitepackages()
    #print("argv1:", sys.argv); sys.stdout.flush()

    s = setup(
        name='effis',
        version='0.2.0',
        description='EFFIS workflow framework',
        long_description=open('README.md').read(),
        #url='https://github.com/CODARcode/cheetah',
        
        package_dir={'': 'src'},

        packages=find_namespace_packages(where='src', include=['effis.composition', 'effis.runtime']),
        #packages=find_namespace_packages(where='src', include=['effis.composition', 'effis.cpp']),
        #package_data={'effis.cpp': ["effis.hpp", "libeffis*", "EffisConfig.cmake"]},
        #include_package_data=True,
        #cmdclass={
        #    #'egg_info': egg_info,
        #    #'dist_info': dist_info,
        #    #'editable_wheel': editable_wheel,
        #    'build_py': CustomInstallPy,
        #    }
    )

    """
    print("command_obj:", s.command_obj.keys()); sys.stdout.flush()
   
    k = "install"
    if k in s.command_obj:
        print(s.command_obj[k].__dict__.keys()); sys.stdout.flush()
        for key in s.command_obj[k].__dict__.keys():
            #if key != "config_vars":
            print(key, s.command_obj[k].__dict__[key])

    if 'editable_wheel' in s.command_obj:
        print("using editable"); sys.stdout.flush()
    """
