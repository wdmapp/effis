#!/usr/bin/env python3
##############################################################################
#
#   edge_writer.py
#
##############################################################################
#
# One-dimensional advection-diffusion system solved by FTCS scheme
# This is a simple model to simulate the coupling of 2 regions (core
# and edge) in the WDMApp project.
# Written in Matlab by Julien Dominski:
#    J. Dominski, et al. "Coupling core delta-f and edge total-f gyrokinetic
#    codes with kinetic electron dynamics", 61st Annual Meeting of the
#    APS Division of Plasma Physics Volume 64, Number 11, October 21-25, 2019;
#    Fort Lauderdale, Florida
#
# This "edge_writer.py" code simulates the "edge" part where the perturbation
# comes from. It writes the data from the buffer zone into a file using
# ADIOS2 for the core_reader to read.
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

# Initialize ADIOS, use SST engine for coupling
comm = MPI.COMM_WORLD
adios = adios2.ADIOS(comm, adios2.DebugON)
#@effis-init comm=comm
#@effis-begin "Coupling"->"Coupling"
io = adios.DeclareIO("Coupling")
# The "engine" gets defined in the effis yaml file
###io.SetEngine('SST')
###io.SetParameter('RendezvousReaderCount', '1')


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
f_edge = np.zeros(n, dtype=np.float)
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


# Initial perturbation in the "edge" region (just a sinusoidal "bump")
for i in range(n4, n):
    f_edge[i] = 0.6*np.sin(2.0*np.pi*dh*(i))


# Prepare ADIOS data to be written
rank = 0
size = 1
nelems = n4-n3   # should be 20
v_buffer = np.zeros(nelems, dtype=np.float)

GlobalDims = [size * nelems]
Offsets = [rank *nelems]
LocalDims = [nelems]
vBuffer = io.DefineVariable("v_buffer", v_buffer, GlobalDims, Offsets, LocalDims)
engine = io.Open("Buffer_data.bp", adios2.Mode.Write, comm)

# Creating plot figure for "EDGE"
fig_e = plt.figure('EDGE', figsize=[8.0, 2.5], frameon=False)
manager_e = plt.get_current_fig_manager()
manager_e.window.setGeometry(100, 590, 1000, 500)
ax_e = fig_e.add_subplot(111)
#line_e, = ax_e.plot(xn, f_edge) # Returns a tuple of line objects, thus the comma
line_e, = ax_e.plot(xn[0:n], f_edge[0:n]) # Returns a tuple of line objects, thus the comma
plt.axis([xn[0], xn[-1], -0.05, 1.0])
plt.axvline(x=80.0, linestyle='dashed', color='r')
plt.axvline(x=60.0, color='r')
plt.axvline(x=40.0, linestyle='dashed', color='r')
rect_e = plt.Rectangle([40.0,0.80], n3, 0.2, facecolor='red', edgecolor='red')
ax_e.add_patch(rect_e)
ax_e.text(85.0, 0.85, 'EDGE', fontsize=14)
ax_e.text(64.0, 0.85, 'BUFFER', fontsize=14)
ax_e.text(42.0, 0.85, 'OVERLAP', fontsize=14)
ax_e.text(25.0, 0.85, 'CORE', fontsize=14)

# Time advance loop
for istep in range(1, nstep):
    f_edge=push(f_edge,y,dt,dh,n,D_coeff)
    #@effis-timestep physical=istep*0.005, number=istep
    if np.mod(istep, nstep_sync) == 0 :
         v_buffer = f_edge[n3:n4]
         engine.BeginStep()
         v = io.InquireVariable("v_buffer")
         engine.Put(v, v_buffer)
         engine.EndStep()
    #line_e.set_ydata(f_edge[n2:n])
    line_e.set_ydata(f_edge[0:n])
    fig_e.canvas.draw()
    fig_e.canvas.flush_events()
    if istep == (nstep-1):
       plt.pause(5.0)
    plt.pause(0.02)

engine.Close()
#@effis-end
#@effis-finalize

# End of program
