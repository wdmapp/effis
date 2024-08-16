#!/usr/bin/env python3
##############################################################################
#
#   core_reader.py
#
##############################################################################
# One-dimensional advection-diffusion system solved by FTCS scheme
# This is a simple model to simulate the coupling of 2 regions (core
# and edge) in the WDMApp project.
# Written in Matlab by Julien Dominski:
#    J. Dominski, et al. "Coupling core delta-f and edge total-f gyrokinetic
#    codes with kinetic electron dynamics", 61st Annual Meeting of the
#    APS Division of Plasma Physics Volume 64, Number 11, October 21-25, 2019;
#    Fort Lauderdale, Florida
#
#
# This "core_reader.py" code simulates the "core" part of the coupling, which
# has no initial perturbation. The edge perturbation will enter the region
# via the buffer zone, which is read using ADIOS2 at the synchronization
# times.
#
##############################################################################
#import sys
from mpi4py import MPI
import adios2
import numpy as np
import matplotlib
#import matplotlib.backends.backend_tkagg
#####matplotlib.use('TkAgg')  #Makes my MAC CRASH!!
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from time import sleep
#from math import sin,cos,pi
#from scipy import interpolate

comm = MPI.COMM_WORLD
adios = adios2.ADIOS(comm)
#@effis-init comm=comm
#@effis-begin "Coupling"->"Coupling"
io = adios.DeclareIO("Coupling")

# The engine is set in the yaml file
#####io.SetEngine('SST')
reader_io = io.Open("Buffer_data.bp", adios2.Mode.Read, comm)

# Run parameters
n = 101
nstep = 250
#nstep = 100
length = 2.0         # Length of spatial 1D domain
dh = -length/(n-1)
dt = 0.005           # time step for time-advanced algorithm
D_coeff = 0.01       # Diffusion coefficient
t_time = 0.0
nstep_sync = 20      # Synchronize buffer region every nstep_sync

# Create 3 numpy arrays of length "n" and initialize with zeros
# So "core"region has no initial perturbation
f_core = np.zeros(n, dtype=np.float)
y = np.zeros(n, dtype=np.float)
xn = np.zeros(n, dtype=np.float)

# Define the domain in terms of regions: core, overlap, buffer, edge
n1 = 1   # n1-n2 is core region
n2 = 40  # n2-n3 is overlap region
n3 = 60  # n3-n4 is buffer region
n4 = 80  # n4-n  is edge region

xn = np.linspace(0., 100.0, n)

def push(f,y,dt,h,n,D_coeff):
    y = f
    for i in range(1,n-1):
        f[i] = y[i] - 0.5*(dt/h)*(y[i+1]-y[i-1]) + D_coeff*(dt/(h*h))*(y[i+1]-2.0*y[i]+y[i-1])
    f[n-1] = 0.0
    f[0] = 0.0
    return f

# Declare data that will be read
nelems = n4-n3   # should be 20
v_buffer = np.zeros(nelems, dtype=np.float)

# Creating plot figure for "CORE"
fig_c = plt.figure('CORE', figsize=[8.0, 2.5])
manager_c = plt.get_current_fig_manager()
manager_c.window.setGeometry(100, 60, 1000, 500)
ax_c = fig_c.add_subplot(111)
line_c, = ax_c.plot(xn[0:n4+1], f_core[0:n4+1]) # Returns a tuple of line objects, thus the comma
plt.axis([xn[0], xn[-1], -0.05, 1.0])
plt.axvline(x=80.0, linestyle='dashed', color='r')
plt.axvline(x=60.0, color='r')
plt.axvline(x=40.0, linestyle='dashed', color='r')
rect_c = plt.Rectangle([0.,0.80], n3, 0.2, facecolor='red', edgecolor='red')
ax_c.add_patch(rect_c)
ax_c.text(85.0, 0.85, 'EDGE', fontsize=14)
ax_c.text(64.0, 0.85, 'BUFFER', fontsize=14)
ax_c.text(42.0, 0.85, 'OVERLAP', fontsize=14)
ax_c.text(25.0, 0.85, 'CORE', fontsize=14)


# Time advance loop
for istep in range(1, nstep):
    f_core=push(f_core,y,dt,dh,n,D_coeff)
    if np.mod(istep, nstep_sync) == 0 :
         while True:
              stepstatus = reader_io.BeginStep(adios2.StepMode.Read, 2)
              if stepstatus == adios2.StepStatus.NotReady:
                 plt.pause(0.02)
                 continue
              elif stepstatus == adios2.StepStatus.OK:
                   break
              else:
                 print("Something went wrong while reading data")
                 break
         
         print(reader_io.CurrentStep())
         varid = io.InquireVariable("v_buffer")
         reader_io.Get(varid, v_buffer)
         reader_io.EndStep()
         f_core[n3:n4] = v_buffer
    
    line_c.set_ydata(f_core[0:(n4+1)])
    fig_c.canvas.draw()
    fig_c.canvas.flush_events()
    if istep == (nstep-1):
       plt.pause(5.0)
    plt.pause(0.02)

reader_io.Close()
#@effis-end
#@effis-finalize

# End of program
