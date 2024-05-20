import matplotlib.pyplot as plt
import sys
import adios2

# Source directory of OCCAMI
#occami_source_dir = '/u/rnies/occami/source'
occami_source_dir = '/ccs/home/esuchyta/software/src/occami/source'
sys.path.append(occami_source_dir)
from occami_island import occami_island

# Island object
island_obj = occami_island(W_i=0.2, M=2, N=1, eqdsk_file="g521022.01000")

# Evaluate GK coefficients
sigma   = 0.5
alpha_0 = 0
phi_vals, bmag_array, gradpar_array, gds2_array, gds21_array, gds22_array, gbdrift_array,\
		cvdrift_array, gbdrift0_array, cvdrift0_array, shat, iota_h =\
		island_obj.get_GK_coefficients_in_magnetic_island_geometry(sigma=sigma, alpha_0=alpha_0,\
		Nphi=201, Nturns=1, turns_island_or_torus="island")


Start = [0]
Size = [phi_vals.shape[0]]
stream = adios2.Stream("GK-Coefficients.bp", "w")
stream.write("phi_vals", phi_vals, Size, Start, Size)
stream.write("bmag", bmag_array, Size, Start, Size)
stream.write("gds2", gds2_array, Size, Start, Size)
stream.write("gds21", gds21_array, Size, Start, Size)
stream.write("gds22", gds22_array, Size, Start, Size)
stream.write("gradpar", gradpar_array, Size, Start, Size)
stream.write("gbdrift", gbdrift_array, Size, Start, Size)
stream.write("gbdrift0", gbdrift_array, Size, Start, Size)
stream.close()


# Plot
fig = plt.figure(figsize=(10,5))
fig.suptitle(r"$\sigma = %.2f, \alpha_0 = %.2f, \iota_h = %.2e, \hat s = %.2e$" % (sigma, alpha_0, iota_h, shat))

gs = fig.add_gridspec(2,4)
axs = []

ax = fig.add_subplot(gs[:,0])
ax.plot(phi_vals, bmag_array)
ax.set_ylabel("bmag")
axs.append(ax)

ax = fig.add_subplot(gs[0,1])
ax.plot(phi_vals, gds2_array)
ax.set_ylabel("gds2")
axs.append(ax)

ax = fig.add_subplot(gs[0,2])
ax.plot(phi_vals, gds21_array)
ax.set_ylabel("gds21")
axs.append(ax)

ax = fig.add_subplot(gs[0,3])
ax.plot(phi_vals, gds22_array)
ax.set_ylabel("gds22")
axs.append(ax)

ax = fig.add_subplot(gs[1,1])
ax.plot(phi_vals, gradpar_array)
ax.set_ylabel("gradpar")
axs.append(ax)

ax = fig.add_subplot(gs[1,2])
ax.plot(phi_vals, gbdrift_array)
ax.set_ylabel("gbdrift")
axs.append(ax)

ax = fig.add_subplot(gs[1,3])
ax.plot(phi_vals, gbdrift0_array)
ax.set_ylabel("gbdrift0")
axs.append(ax)


for ax in axs:
	ax.set_xlim([phi_vals[0], phi_vals[-1]])
	ax.grid()
	ax.set_xlabel(r"$\phi$")

fig.tight_layout()
fig.savefig("fig_plot_GK_coefficients.pdf")
