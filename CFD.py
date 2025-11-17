# imports
import numpy as np
import scipy as sc
import matplotlib.pyplot as plt
import torch

# System globals
X_LEN, Y_LEN = 1, 1 # physical size (m)
VOL = X_LEN * Y_LEN
nx, ny = 201, 201 # number of grid points in each axis
dx, dy = X_LEN/nx, Y_LEN/ny
cv_vol = dx*dy
c = 1

T = 1 # length of simulation (s)
nt = 100
dt = T/nt
timesteps = np.linspace(0, T, nt)

# Coordinate system
x = np.linspace(0, X_LEN, nx)
y = np.linspace(-Y_LEN/2, Y_LEN/2, ny)
GRID = np.meshgrid(x, y) # used for plotting

# fluid initialization
u = np.ones((nx, ny)) # initial x velocities
v = np.zeros((nx, ny)) # initial y velocities

rho = 0.4135 # density in kg/m^3, air @ 10k meters. Assuming incompressibility (constant mass density)
k = 0.01 # kinetic viscosity of air. FILL IN TRUE VALUE
nu = 1.5e-5 # kinematic viscosity (m^2/s) for air at standard conditions
F = 1.0 # external forcing term in x-direction
nit = 50 # number of iterations for pressure Poisson solver
u = np.zeros((ny, nx))
v = np.zeros((ny, nx))
p = np.zeros((ny, nx))
b = np.zeros((ny, nx))
cv_mass = rho * cv_vol

# PLOTTING FUNCTIONS

### MOST IMPORTANT BLOCK OF CODE. The System class handles
class System:
    def __init__(self, X_len, Y_len, nx, ny, T, nt, rho, nu):
        """X_len, Y_len: Physial size of grid in meters
        nx, ny: number of grid points
        T: Length of simulation in s
        nt: number of timesteps
        rho: density of fluid in kg/m^3
        nu: kinetic viscosity of fluid
        You MUST use set_ics() and set_body_forces() to specify initial values of the fields"""

        self.X_len, self.Y_len, self.T = X_len, Y_len, T

        # discretization
        self.nx, self.ny, self.nt = nx, ny, nt
        self.dx = self.X_len / self.nx
        self.dy = self.Y_len / self.ny
        self.cv_vol = self.dx * self.dy

        # fluid properties: Density in kg/m^3, air @ 10k meters,
        self.rho, self.nu = rho, nu
        self.cv_mass = self.rho * self.cv_vol

        # time
        self.dt = self.T / self.nt
        self.timesteps = np.linspace(0.0, self.T, self.nt)
        self.step_num = 1

        # coordinates
        self.x = np.linspace(0.0, self.X_len, self.nx)
        self.y = np.linspace(-self.Y_len / 2, self.Y_len / 2, self.ny)
        self.X, self.Y = np.meshgrid(self.x, self.y, indexing="xy")

        # fields (use set_ics() to specify true values)
        self.u = np.empty((self.nx, self.ny))   # x velocities
        self.v = np.empty_like(self.u)  # y velocities
        self.p = np.empty_like(self.u) # pressures
        self.Fx = np.empty_like(self.u) # body forces in x direction
        self.Fy = np.empty_like(self.u) # body forces in y direction


        # histories, initialized in the first call of set_ics
        self.momenta = np.array([])
        self.kes = np.array([])

        # list of obstacles
        self.obstacles = []

        # Obstacle mask for pressure solver (True = inside obstacle/wing)
        self.obstacle_mask = np.zeros((self.nx, self.ny), dtype=bool)


    def set_ics(self, u, v, p):
        self.u = u
        self.v = v
        self.p = p
        if self.momenta.size == 0:
            self.momenta = self.system_momentum()
        if self.kes.size == 0:
            self.kes = self.system_ke()

    def set_body_forces(self, Fx, Fy):
        self.Fx = Fx
        self.Fy = Fy

    def add_obstacle(self, **kwargs):
        obj = Obstacle(**kwargs)
        self.obstacles.append(obj)
        return obj

    def apply_obstacle_bcs(self):
        for obj in self.obstacles:
            obj.apply_no_slip(self)

    def update_obstacle_mask(self):
        """Update the obstacle mask based on all obstacles and wings.
        This should be called whenever obstacles change."""
        self.obstacle_mask = np.zeros((self.nx, self.ny), dtype=bool)
        for obj in self.obstacles:
            mask = obj.obj_mask(self)
            # obj_mask returns shape (ny, nx) from meshgrid, need to transpose
            self.obstacle_mask |= mask.T


    ## METRICS
    def system_ke(self):
        """Calculate total kinetic energy of the fluid with 1/2 * m * v^2
        Note that upon further thought, this shouldn't necessarily be conserved:
        Energy can be stored in higher pressure, eg."""
        return 1/2 * np.sum(self.cv_mass * (self.u**2 + self.v**2))


    def system_momentum(self):
        """Calculate total momentum of the fluid in each direction with m * v"""
        return (np.sum(self.cv_mass * self.u), np.sum(self.cv_mass * self.v))


    def compute_divergence(self):
        """Sanity check of computing the divergence of the velocity field.
        This should be very close to 0 ideally"""

        pass


    ## NS FUNCTIONS
    def motion_step(self):
        u_jmin = np.column_stack((self.u[:, -1], self.u[:, :-1])) # all shifted one right so u_i-1,j is at u_ij
        u_jplus = np.column_stack((self.u[:, 1:], self.u[:, 0])) # shifted one left
        u_imin = np.vstack((self.u[-1], self.u[:-1])) # shifted up
        u_iplus = np.vstack((self.u[1:], self.u[0])) # shifted down

        v_jmin = np.column_stack((self.v[:, -1], self.v[:, :-1]))
        v_jplus = np.column_stack((self.v[:, 1:], self.v[:, 0]))
        v_imin = np.vstack((self.v[-1], self.v[:-1]))
        v_iplus = np.vstack((self.v[1:], self.v[0]))

        p_jmin = np.column_stack((self.p[:, -1], self.p[:, :-1]))
        p_jplus = np.column_stack((self.p[:, 1:], self.p[:, 0]))
        p_imin = np.vstack((self.p[-1], self.p[:-1]))
        p_iplus = np.vstack((self.p[1:], self.p[0]))

        # New values to fill. Order of discretized terms: advection (2 lines), pressure gradient, diffusion (2 lines)
        u_nplus = self.u - self.dt * (self.u * (self.u - u_imin)/self.dx
                                      + self.v * (u_jplus - u_imin) / (2*self.dy)
                                      + (p_iplus - p_imin) / (self.rho*2*self.dx)
                                      - self.nu * (u_iplus - 2*self.u + u_imin) / (self.dx**2)
                                      - self.nu * (u_jplus - 2*self.u + u_jmin) / (self.dy**2)
                                      - self.Fx)

        v_nplus = self.v - self.dt * (self.u * (self.v - v_imin)/self.dx
                                      + self.v * (v_jplus - v_imin) / (2*self.dy)
                                      + (p_jplus - p_jmin) / (self.rho*2*self.dy)
                                      - self.nu * (v_iplus - 2*self.v + v_imin) / (self.dx**2)
                                      - self.nu * (v_jplus - 2*self.v + v_jmin) / (self.dy**2)
                                      - self.Fy)

        self.u = u_nplus
        self.v = v_nplus

        # updating histories
        self.kes = np.append(self.kes, self.system_ke())
        self.momenta = np.vstack((self.momenta, self.system_momentum()))
        self.step_num += 1

        # sanity check that the fields don't contain NaNs or infinities
        a = np.sum(self.u)
        b = np.sum(self.v)
        assert not any((np.isnan(a), np.isnan(b))), f"Unexpected NaN in velocity field at timestep {self.step_num}"
        assert not any((np.isinf(a), np.isneginf(a), np.isinf(b), np.isneginf(b))), f"Unexpected Inf in velocity field at timestep {self.step_num}"


    def pressure_poisson_RHS(self):
        """Attempt to set the divergence of the velocity field of the next step to 0. Doing this yields an
        expression involving the Laplacian of the pressure field, along with spatial derivatives of the
        velocity field in the current step. We set the pressure Laplacian equal to everything else.
        This function evaluates the 'everything else' at the current timestep"""

        u_jmin = np.column_stack((self.u[:, -1], self.u[:, :-1])) # all shifted one right so u_i-1,j is at u_ij
        u_jplus = np.column_stack((self.u[:, 1:], self.u[:, 0])) # shifted one left
        u_imin = np.vstack((self.u[-1], self.u[:-1])) # shifted up
        u_iplus = np.vstack((self.u[1:], self.u[0])) # shifted down

        v_jmin = np.column_stack((self.v[:, -1], self.v[:, :-1]))
        v_jplus = np.column_stack((self.v[:, 1:], self.v[:, 0]))
        v_imin = np.vstack((self.v[-1], self.v[:-1]))
        v_iplus = np.vstack((self.v[1:], self.v[0]))

        # Really this is -RHS, but in the reshuffling of the pressure poisson, this is the correct signage
        RHS = self.rho * (((u_iplus - u_imin) / (2*self.dx))**2
                           + 2 * ((u_jplus - u_jmin) / (2*self.dy)) * ((v_iplus - v_imin) / (2*self.dx))
                           + ((v_jplus - v_jmin) / (2*self.dy))**2
                           - 1/self.dt * ((u_iplus - u_imin)/(2*self.dx) + (v_jplus - v_jmin)/(2*self.dy)))

        # Set RHS to zero inside obstacles (no divergence enforcement needed there)
        if np.any(self.obstacle_mask):
            RHS[self.obstacle_mask] = 0.0

        # sanity check that the fields don't contain NaNs or infinities
        a = np.sum(RHS)
        assert not np.isnan(a), f"Unexpected NaN in poisson RHS field at timestep {self.step_num}"
        assert not any((np.isinf(a), np.isneginf(a))), f"Unexpected Inf in poisson RHS field at timestep {self.step_num}"

        return RHS


    # variant 1: pass in zero pressure and let it equilibriate
    def pressure_step_v0(self):
        """Iterate over pseudotime to equilibriate pressure field such that its laplacian
        matches the calculated RHS"""

        median_delta_ratio = []

        RHS = self.pressure_poisson_RHS()
        p_n = np.zeros_like(self.p) # passing in zero pressures as IC
        diff_prod = self.dx**2 * self.dy**2
        diff_sum = self.dx**2 + self.dy**2

        i = 1
        run = True
        max_iters = 1000

        while i <= max_iters and run:
            p_jmin = np.column_stack((p_n[:, -1], p_n[:, :-1]))
            p_jplus = np.column_stack((p_n[:, 1:], p_n[:, 0]))
            p_imin = np.vstack((p_n[-1], p_n[:-1]))
            p_iplus = np.vstack((p_n[1:], p_n[0]))

            p_nplus = ((self.dy**2 * (p_iplus + p_imin)
                        + self.dx**2 * (p_jplus + p_jmin)) / (2 * diff_sum)
                        + diff_prod / (2 * diff_sum) * RHS)

            delta_p = p_nplus-p_n
            p_n = p_nplus

            median_delta_ratio.append(np.percentile(np.absolute(delta_p/p_n), 95))

            if np.percentile(np.absolute(delta_p/p_n), 95) <= 0.005: # If 95% of pressure values are changing by less than half a percent we break
                run = False

            i += 1


        a = np.sum(p_n)
        assert not np.isnan(a), f"Unexpected NaN in pressure field at timestep {self.step_num}"
        assert not any((np.isinf(a), np.isneginf(a))), f"Unexpected Inf in pressure field at timestep {self.step_num}"

        return p_n, median_delta_ratio, i


    # Diff method of pseudotime stepping. Considerably slower
    def pressure_step_v1(self):
        """Iterate over pseudotime to equilibriate pressure field such that its laplacian
        matches the calculated RHS"""

        nit = 100 # for now used fix number of iteration and see scale of pressure changes to find right tolerance
        max_deltas = []
        RHS = self.pressure_poisson_RHS()
        p_n = np.zeros_like(self.p) # passing in zero pressures as IC

        diff_prod = self.dx**2 * self.dy**2
        diff_sum = self.dx**2 + self.dy**2

        for i in range(nit):
            p_nplus = np.empty_like(p_n)

            ## Center
            p_nplus[1:-1, 1:-1] = ((self.dy**2 * (p_n[1:-1, 2:] + p_n[1:-1, :-2])
                                   + self.dx**2 * (p_n[2:, 1:-1] + p_n[:-2, 1:-1])) / (2 * diff_sum)
                                   + diff_prod / (2 * diff_sum) * RHS[1:-1, 1:-1])

            ## Edges
            # x = 0
            p_nplus[1:-1, 0] = ((self.dy**2 * (p_n[1:-1, 2] + p_n[1:-1, -1])
                                   + self.dx**2 * (p_n[2:, 0] + p_n[:-2, 0])) / (2 * diff_sum)
                                   + diff_prod / (2 * diff_sum) * RHS[1:-1, 0])

            # x = -1
            p_nplus[1:-1, -1] = ((self.dy**2 * (p_n[1:-1, 0] + p_n[1:-1, -2])
                                   + self.dx**2 * (p_n[2:, -1] + p_n[:-2, -1])) / (2 * diff_sum)
                                   + diff_prod / (2 * diff_sum) * RHS[1:-1, -1])

            # y = 0
            p_nplus[0, 1:-1] = ((self.dy**2 * (p_n[0, 2:] + p_n[0, :-2])
                                   + self.dx**2 * (p_n[1, 1:-1] + p_n[-1, 1:-1])) / (2 * diff_sum)
                                   + diff_prod / (2 * diff_sum) * RHS[0, 1:-1])

            # y = -1
            p_nplus[-1, 1:-1] = ((self.dy**2 * (p_n[-1, 2:] + p_n[-1, :-2])
                                   + self.dx**2 * (p_n[0, 1:-1] + p_n[-2, 1:-1])) / (2 * diff_sum)
                                   + diff_prod / (2 * diff_sum) * RHS[-1, 1:-1])

            ## Corners
            p_nplus[0, 0] = ((self.dy**2 * (p_n[0, 1] + p_n[0, -1])
                                   + self.dx**2 * (p_n[1, 0] + p_n[-1, 0])) / (2 * diff_sum)
                                   + diff_prod / (2 * diff_sum) * RHS[0, 0])

            p_nplus[0, -1] = ((self.dy**2 * (p_n[0, 0] + p_n[0, -2])
                                   + self.dx**2 * (p_n[1, 0] + p_n[-1, 0])) / (2 * diff_sum)
                                   + diff_prod / (2 * diff_sum) * RHS[0, -1])

            p_nplus[-1, 0] = ((self.dy**2 * (p_n[-1, 1] + p_n[-1, -1])
                                   + self.dx**2 * (p_n[0, 0] + p_n[-2, 0])) / (2 * diff_sum)
                                   + diff_prod / (2 * diff_sum) * RHS[-1, 0])

            p_nplus[-1, -1] = ((self.dy**2 * (p_n[-1, 0] + p_n[-1, -2])
                                   + self.dx**2 * (p_n[0, -1] + p_n[-2, -1])) / (2 * diff_sum)
                                   + diff_prod / (2 * diff_sum) * RHS[-1, -1])

            delta_p = p_nplus-p_n
            max_deltas.append(np.max(delta_p))
            p_n = p_nplus

        return p_n, max_deltas



    # variant 2: pass in previous pressure values, which we assume will be similar to desired values
    def pressure_step_v2(self):
        """Improved pressure Poisson solver with proper handling of internal boundaries (obstacles/wings).

        Uses:
        - Periodic boundary conditions at domain edges
        - Neumann boundary conditions (zero pressure gradient) at obstacle surfaces
        - Modified stencils near obstacles when full 4-point stencil is unavailable
        """

        RHS = self.pressure_poisson_RHS()

        p_n = self.p.copy() # passing in previous pressure as IC
        diff_prod = self.dx**2 * self.dy**2
        diff_sum = self.dx**2 + self.dy**2

        i = 1
        run = True
        max_iters = 10000

        # Pre-compute neighbor availability for each point
        # A neighbor is available if it's not inside an obstacle
        has_left = np.ones((self.nx, self.ny), dtype=bool)
        has_right = np.ones((self.nx, self.ny), dtype=bool)
        has_down = np.ones((self.nx, self.ny), dtype=bool)
        has_up = np.ones((self.nx, self.ny), dtype=bool)

        # Check if neighbors are inside obstacles
        if np.any(self.obstacle_mask):
            # Left neighbor (i-1, j)
            has_left[1:, :] = ~self.obstacle_mask[:-1, :]
            has_left[0, :] = ~self.obstacle_mask[-1, :]  # periodic

            # Right neighbor (i+1, j)
            has_right[:-1, :] = ~self.obstacle_mask[1:, :]
            has_right[-1, :] = ~self.obstacle_mask[0, :]  # periodic

            # Down neighbor (i, j-1)
            has_down[:, 1:] = ~self.obstacle_mask[:, :-1]
            has_down[:, 0] = ~self.obstacle_mask[:, -1]  # periodic

            # Up neighbor (i, j+1)
            has_up[:, :-1] = ~self.obstacle_mask[:, 1:]
            has_up[:, -1] = ~self.obstacle_mask[:, 0]  # periodic

        while i <= max_iters and run:
            p_old = p_n.copy()

            # Standard periodic wrapping for neighbor access
            # Left neighbor (i-1, j): wrap last row to first
            p_left = np.vstack((p_old[-1:, :], p_old[:-1, :]))
            # Right neighbor (i+1, j): wrap first row to last
            p_right = np.vstack((p_old[1:, :], p_old[:1, :]))
            # Down neighbor (i, j-1): wrap last column to first
            p_down = np.column_stack((p_old[:, -1:], p_old[:, :-1]))
            # Up neighbor (i, j+1): wrap first column to last
            p_up = np.column_stack((p_old[:, 1:], p_old[:, :1]))

            # For points inside obstacles, keep pressure at zero (arbitrary reference)
            if np.any(self.obstacle_mask):
                p_left[self.obstacle_mask] = 0
                p_right[self.obstacle_mask] = 0
                p_down[self.obstacle_mask] = 0
                p_up[self.obstacle_mask] = 0

            # Apply Neumann BC (zero gradient) at obstacle boundaries
            # If a neighbor is inside obstacle, use current point's value (zero gradient)
            p_left = np.where(has_left, p_left, p_old)
            p_right = np.where(has_right, p_right, p_old)
            p_down = np.where(has_down, p_down, p_old)
            p_up = np.where(has_up, p_up, p_old)

            # Compute new pressure using standard 5-point stencil
            # The Neumann BC is already enforced by replacing missing neighbors with current value
            p_nplus = ((self.dy**2 * (p_right + p_left)
                        + self.dx**2 * (p_up + p_down)) / (2 * diff_sum)
                        + diff_prod / (2 * diff_sum) * RHS)

            # Keep pressure inside obstacles at zero (reference pressure)
            if np.any(self.obstacle_mask):
                p_nplus[self.obstacle_mask] = 0.0

            # Compute change
            delta_p = p_nplus - p_n
            p_n = p_nplus

            # Convergence check (only for fluid points, not obstacle interior)
            if np.any(self.obstacle_mask):
                fluid_mask = ~self.obstacle_mask
                p_n_fluid = p_n[fluid_mask]
                delta_p_fluid = delta_p[fluid_mask]

                # Avoid division by zero
                with np.errstate(divide='ignore', invalid='ignore'):
                    relative_change = np.abs(delta_p_fluid / (p_n_fluid + 1e-10))
                    relative_change = relative_change[np.isfinite(relative_change)]

                if len(relative_change) > 0:
                    if np.percentile(relative_change, 95) <= 0.001:
                        run = False
            else:
                # No obstacles, use standard convergence check
                with np.errstate(divide='ignore', invalid='ignore'):
                    relative_change = np.abs(delta_p / (p_n + 1e-10))
                    relative_change = relative_change[np.isfinite(relative_change)]

                if len(relative_change) > 0:
                    if np.percentile(relative_change, 95) <= 0.001:
                        run = False

            i += 1

        a = np.sum(p_n)
        assert not np.isnan(a), f"Unexpected NaN in pressure field at timestep {self.step_num}"
        assert not any((np.isinf(a), np.isneginf(a))), f"Unexpected Inf in pressure field at timestep {self.step_num}"

        return p_n, i



    ## PLOTTING FUNCTIONS
    """All plotting functions share some of the same arguments:
    show_plot (bool, default False) specifies whether plt.show() will be called at to display the figure
    save_plot (bool, default False) specifies whether plt.savefig() will be called to save the figure to file
    fname (bool/str, default False). If save_plot = True and fname is given some
    """


    # NOT UPDATED
    def plot_pressures(p, X, Y, contour_style=False, show_plot=False, cmap='viridis'):
        """Make a heatmap plot of p (2D array of pressures). Contour lines are added if contour_style is true"""

        fig, ax = plt.subplots(figsize=(10, 8))

        # plotting the pressure field as a contour
        ax.contourf(X, Y, p, alpha=0.5, cmap=cmap)

        #plotting the pressure field outlines
        if contour_style:
            ax.contour(X, Y, p, cmap=cmap)

        if show_plot:
            plt.show()

        return fig


    def plot_velocities(self, vector_style=True, show_plot=False, stride_factor=20, stream_density=(1, 1), color=False, cmap='inferno', save_plot=False):
        '''Make a plot of the velocity field.
        If vector_style is True, use matplotlib quiver(), if False, use matplotlib streamplot()'''

        #determine stride
        sx = self.nx // stride_factor
        sy = self.ny // stride_factor

        X_plot, Y_plot = self.X[::sx, ::sy], self.Y[::sx, ::sy]
        u_plot, v_plot = self.u[::sx, ::sy], self.v[::sx, ::sy]

        fig, ax = plt.subplots(figsize=(10, 8))

        #plot
        if color:
            C = np.hypot(u_plot, v_plot)
            if vector_style:
                ax.quiver(X_plot, Y_plot, u_plot, v_plot, C, cmap=cmap)
            else:
                ax.streamplot(X_plot, Y_plot, u_plot, v_plot, density=stream_density, color=C, cmap=cmap)
        else:
            if vector_style:
                ax.quiver(X_plot, Y_plot, u_plot, v_plot)
            else:
                ax.streamplot(X_plot, Y_plot, u_plot, v_plot, density=stream_density)

        if show_plot:
            plt.show()

        if save_plot:
            plt.savefig(f"Velocities @ timestep {self.step_num}.png")

        return fig


    def plot_state(self, p_cmap='viridis', stride_factor=20, stream_density=(1, 1), vector_style=True, contour_style=False, show_plot=False, save_plot=False, fname=False):
        """Overlay velocity and pressure heatmap plots into one visualization. """

        sx = self.nx // stride_factor
        sy = self.ny // stride_factor

        X_plot, Y_plot = self.X[::sx, ::sy], self.Y[::sx, ::sy]
        u_plot, v_plot = self.u[::sx, ::sy], self.v[::sx, ::sy]

        fig, ax = plt.subplots(figsize=(10, 8))

        # plot pressure field (first so that velocities lay on top)
        ax.contourf(self.X, self.Y, self.p, alpha=0.5, cmap=p_cmap)
        if contour_style:
            ax.contour(self.X, self.Y, self.p, cmap=p_cmap)

        #plot velocities
        if vector_style:
            ax.quiver(X_plot, Y_plot, u_plot, v_plot)
        else:
            ax.streamplot(X_plot, Y_plot, u_plot, v_plot, density=stream_density, color='black')

        if save_plot:
            if not fname:
                plt.savefig(f"State @ timestep {self.step_num}.png")
            else:
                assert isinstance(fname, str), "Filename datatype to save state plot at is not a string."
                plt.savefig(fname)

        if show_plot:
            plt.show()

        plt.close()


    def plot_system_momentum(self, show_plot=False):
        """Plots side-by-side figures showing x and y momentum at each time step"""

        fig, [ax1, ax2] = plt.subplots(nrows=2, ncols=1, figsize=(8, 10))

        ax1.plot(self.timesteps, self.momenta[:, 0]) # x momentum
        ax2.plot(self.timesteps, self.momenta[:, 1]) # y momentum

        ax1.set_title('X momentum')
        ax2.set_title('Y momentum')
        ax2.set_xlabel('Time')
        ax1.set_ylabel('momentum')
        ax2.set_ylabel('momentum')


    def plot_system_ke(self, show_plot=False):
        """Plot kinetic energy values. Very similar to plot_system_momentum but just a single plot"""

        fig, ax = plt.subplots(figsize=(8, 5))

        ax.plot(self.timesteps, self.kes)

        ax.set_title('System Kinetic Energy vs Time')
        ax.set_xlabel('Time')
        ax.set_ylabel('Kinetic Energy')

        if show_plot:
            plt.show()

        return fig


## Obstacle Class
class Obstacle:
    def __init__(self, cx, cy, shape='circle', radius=None, width=None, height=None):
        """Shape: 'circle' or 'rectangle'
        cx, cy: coordinates for center
        radius: radius if shape is 'circle'
        width, height: dimensions if shape is 'rectangle' """

        self.cx, self.cy, self.shape, self.radius, self.width, self.height = cx, cy, shape, radius, width, height


  # Boolean mask of obstacle
    def obj_mask(self, system: System):
        X, Y = system.X, system.Y
        if self.shape == "circle":
            return (X-self.cx)**2 + (Y-self.cy)**2 <= self.radius**2
        elif self.shape == "rectangle":
            return (np.abs(X - self.cx) <= self.width / 2) & (np.abs(Y - self.cy) <= self.height / 2)
        else:
          return ValueError(f'Obstacle type {self.shape} not implemented yet')

    # applies no-slip on object
    def apply_no_slip(self, system: System):
        m = self.obj_mask(system)
        system.u[m] = 0.0
        system.v[m] = 0.0

# NS functions

def u_advection(u, v, inflow_vel):
    '''Calculate advection of x momentum into a control volume
    Uses BD for x spatial derivatives and CD for y spatial derivatives (x flow is directed, y is not)
    Periodic boundary conditions in both directions
    '''

    global dx, dy

    adv = np.zeros_like(u)

    u_imin = np.hstack((u[None, -1].T, u[:, :-1]), axis=1) # all shifted one right so u_i-1,j is at u_ij
    u_jplus = np.vstack((u[1:], u[0]))
    u_jmin = np.vstack((u[-1], u[:-1]))

    adv = u * (u - u_imin)/dx + v * (u_jplus - u_jmin)/2/dy

    return adv


def v_advection(u, v):
    '''Identical to u_advection() but for y momentum advection'''

    adv = np.zeros_like(v)

    v_imin = np.hstack((v[None, -1].T, v[:, :-1]), axis=1) # all shifted one right so u_i-1,j is at u_ij
    v_jplus = np.vstack((v[1:], v[0])) # shifted down
    v_jmin = np.vstack((v[-1], v[:-1])) # shifted up

    adv = u * (v - v_imin)/dx + v * (v_jplus - v_jmin)/2/dy

    return adv


def u_diffusion(u, v, k):
    '''Calculate diffusion term as kin_visc * del^2 u using central differences

    '''

    #diff = np.zeros_like(u)

    #diff[1:-1, 1:-1] =


def v_diffusion(u, v, k):
    '''Identical to u_advection but for x momentum'''
    pass


def system_ke(u, v):
    '''Calculate total kinetic energy of the fluid with 1/2 * m * v^2
    Returns a float: KE'''

    global cv_mass
    return 1/2 * np.sum(cv_mass * (u**2 + v**2))


def system_momentum(u, v):
    '''Calculate total momentum of the fluid with m * v for each direction
    Returns a tuple: (p_u, p_v)'''

    global cv_mass
    return (np.sum(cv_mass * u), np.sum(cv_mass * v))

def plot2D(x, y, p):
    fig = pyplot.figure(figsize=(11, 7), dpi=100)
    ax = fig.add_subplot(111,projection='3d')
    X, Y = np.meshgrid(x, y)
    surf = ax.plot_surface(X, Y, p[:], rstride=1, cstride=1, cmap=cm.viridis,
            linewidth=0, antialiased=False)
    ax.view_init(30, 225)
    ax.set_xlabel('$x$')
    ax.set_ylabel('$y$')
    
def cavity_flow(nt, u, v, dt, dx, dy, p, rho, nu):
    un = np.empty_like(u)
    vn = np.empty_like(v)
    b = np.zeros((ny, nx))
    
    for n in range(nt):
        un = u.copy()
        vn = v.copy()
        
        b = build_up_b(b, rho, dt, u, v, dx, dy)
        p = pressure_poisson(p, dx, dy, b)
        
        u[1:-1, 1:-1] = (un[1:-1, 1:-1]-
                         un[1:-1, 1:-1] * dt / dx *
                        (un[1:-1, 1:-1] - un[1:-1, 0:-2]) -
                         vn[1:-1, 1:-1] * dt / dy *
                        (un[1:-1, 1:-1] - un[0:-2, 1:-1]) -
                         dt / (2 * rho * dx) * (p[1:-1, 2:] - p[1:-1, 0:-2]) +
                         nu * (dt / dx**2 *
                        (un[1:-1, 2:] - 2 * un[1:-1, 1:-1] + un[1:-1, 0:-2]) +
                         dt / dy**2 *
                        (un[2:, 1:-1] - 2 * un[1:-1, 1:-1] + un[0:-2, 1:-1])))

        v[1:-1,1:-1] = (vn[1:-1, 1:-1] -
                        un[1:-1, 1:-1] * dt / dx *
                       (vn[1:-1, 1:-1] - vn[1:-1, 0:-2]) -
                        vn[1:-1, 1:-1] * dt / dy *
                       (vn[1:-1, 1:-1] - vn[0:-2, 1:-1]) -
                        dt / (2 * rho * dy) * (p[2:, 1:-1] - p[0:-2, 1:-1]) +
                        nu * (dt / dx**2 *
                       (vn[1:-1, 2:] - 2 * vn[1:-1, 1:-1] + vn[1:-1, 0:-2]) +
                        dt / dy**2 *
                       (vn[2:, 1:-1] - 2 * vn[1:-1, 1:-1] + vn[0:-2, 1:-1])))

        u[0, :]  = 0
        u[:, 0]  = 0
        u[:, -1] = 0
        u[-1, :] = 1    # set velocity on cavity lid equal to 1
        v[0, :]  = 0
        v[-1, :] = 0
        v[:, 0]  = 0
        v[:, -1] = 0
        
        
    return u, v, p

def laplace2d(p, y, dx, dy, l1norm_target):
    l1norm = 1
    pn = np.empty_like(p)

    while l1norm > l1norm_target:
        pn = p.copy()
        p[1:-1, 1:-1] = ((dy**2 * (pn[1:-1, 2:] + pn[1:-1, 0:-2]) +
                         dx**2 * (pn[2:, 1:-1] + pn[0:-2, 1:-1])) /
                        (2 * (dx**2 + dy**2)))
            
        p[:, 0] = 0  # p = 0 @ x = 0
        p[:, -1] = y  # p = y @ x = 2
        p[0, :] = p[1, :]  # dp/dy = 0 @ y = 0
        p[-1, :] = p[-2, :]  # dp/dy = 0 @ y = 1
        l1norm = (np.sum(np.abs(p[:]) - np.abs(pn[:])) /
                np.sum(np.abs(pn[:])))
     
    return p

def build_up_b(rho, dt, dx, dy, u, v):
    """Isolating a portion of the transposed equation to make it easier to parse. 
    We have periodic boundary conditions throughout this grid, so we need to explicitly calculate the values at the leading 
    and trailing edge of our `u` vector."""
    b = np.zeros_like(u)
    b[1:-1, 1:-1] = (rho * (1 / dt * ((u[1:-1, 2:] - u[1:-1, 0:-2]) / (2 * dx) +
                                      (v[2:, 1:-1] - v[0:-2, 1:-1]) / (2 * dy)) -
                            ((u[1:-1, 2:] - u[1:-1, 0:-2]) / (2 * dx))**2 -
                            2 * ((u[2:, 1:-1] - u[0:-2, 1:-1]) / (2 * dy) *
                                 (v[1:-1, 2:] - v[1:-1, 0:-2]) / (2 * dx))-
                            ((v[2:, 1:-1] - v[0:-2, 1:-1]) / (2 * dy))**2))
    
    # Periodic BC Pressure @ x = 2
    b[1:-1, -1] = (rho * (1 / dt * ((u[1:-1, 0] - u[1:-1,-2]) / (2 * dx) +
                                    (v[2:, -1] - v[0:-2, -1]) / (2 * dy)) -
                          ((u[1:-1, 0] - u[1:-1, -2]) / (2 * dx))**2 -
                          2 * ((u[2:, -1] - u[0:-2, -1]) / (2 * dy) *
                               (v[1:-1, 0] - v[1:-1, -2]) / (2 * dx)) -
                          ((v[2:, -1] - v[0:-2, -1]) / (2 * dy))**2))

    # Periodic BC Pressure @ x = 0
    b[1:-1, 0] = (rho * (1 / dt * ((u[1:-1, 1] - u[1:-1, -1]) / (2 * dx) +
                                   (v[2:, 0] - v[0:-2, 0]) / (2 * dy)) -
                         ((u[1:-1, 1] - u[1:-1, -1]) / (2 * dx))**2 -
                         2 * ((u[2:, 0] - u[0:-2, 0]) / (2 * dy) *
                              (v[1:-1, 1] - v[1:-1, -1]) / (2 * dx))-
                         ((v[2:, 0] - v[0:-2, 0]) / (2 * dy))**2))
    
    return b

def pressure_poisson_periodic(p, dx, dy):
    """ Defined to help segregate the different rounds of calculations. 
    Helps ensure a divergence-free field."""
    pn = np.empty_like(p)
    
    for q in range(nit):
        pn = p.copy()
        p[1:-1, 1:-1] = (((pn[1:-1, 2:] + pn[1:-1, 0:-2]) * dy**2 +
                          (pn[2:, 1:-1] + pn[0:-2, 1:-1]) * dx**2) /
                         (2 * (dx**2 + dy**2)) -
                         dx**2 * dy**2 / (2 * (dx**2 + dy**2)) * b[1:-1, 1:-1])

        # Periodic BC Pressure @ x = 2
        p[1:-1, -1] = (((pn[1:-1, 0] + pn[1:-1, -2])* dy**2 +
                        (pn[2:, -1] + pn[0:-2, -1]) * dx**2) /
                       (2 * (dx**2 + dy**2)) -
                       dx**2 * dy**2 / (2 * (dx**2 + dy**2)) * b[1:-1, -1])

        # Periodic BC Pressure @ x = 0
        p[1:-1, 0] = (((pn[1:-1, 1] + pn[1:-1, -1])* dy**2 +
                       (pn[2:, 0] + pn[0:-2, 0]) * dx**2) /
                      (2 * (dx**2 + dy**2)) -
                      dx**2 * dy**2 / (2 * (dx**2 + dy**2)) * b[1:-1, 0])
        
        # Wall boundary conditions, pressure
        p[-1, :] =p[-2, :]  # dp/dy = 0 at y = 2
        p[0, :] = p[1, :]  # dp/dy = 0 at y = 0
    
    return p

def channel_flow_solver(u, v, p, rho, dt, dx, dy, nu, F, tolerance=0.001):
    """Solve 2D flow using incompressible Navier-Stokes equations with fully periodic boundaries.

    Implements periodic boundary conditions in both x and y directions, simulating an infinite
    domain suitable for atmospheric flow analysis (e.g., wing optimization). The top boundary
    wraps to the bottom and vice versa, allowing flow to spread infinitely without wall constraints.
    
    Top boundary (u[-1, :] and v[-1, :]) now references bottom values (un[0, :], vn[0, :])
    Bottom boundary (u[0, :] and v[0, :]) now references top values (un[-1, :], vn[-1, :])
    """

    udiff = 1
    stepcount = 0

    while udiff > tolerance:
        un = u.copy()
        vn = v.copy()

        b = build_up_b(rho, dt, dx, dy, u, v)
        p = pressure_poisson_periodic(p, dx, dy)

        # Interior points
        u[1:-1, 1:-1] = (un[1:-1, 1:-1] -
                         un[1:-1, 1:-1] * dt / dx *
                        (un[1:-1, 1:-1] - un[1:-1, 0:-2]) -
                         vn[1:-1, 1:-1] * dt / dy *
                        (un[1:-1, 1:-1] - un[0:-2, 1:-1]) -
                         dt / (2 * rho * dx) *
                        (p[1:-1, 2:] - p[1:-1, 0:-2]) +
                         nu * (dt / dx**2 *
                        (un[1:-1, 2:] - 2 * un[1:-1, 1:-1] + un[1:-1, 0:-2]) +
                         dt / dy**2 *
                        (un[2:, 1:-1] - 2 * un[1:-1, 1:-1] + un[0:-2, 1:-1])) +
                         F * dt)

        v[1:-1, 1:-1] = (vn[1:-1, 1:-1] -
                         un[1:-1, 1:-1] * dt / dx *
                        (vn[1:-1, 1:-1] - vn[1:-1, 0:-2]) -
                         vn[1:-1, 1:-1] * dt / dy *
                        (vn[1:-1, 1:-1] - vn[0:-2, 1:-1]) -
                         dt / (2 * rho * dy) *
                        (p[2:, 1:-1] - p[0:-2, 1:-1]) +
                         nu * (dt / dx**2 *
                        (vn[1:-1, 2:] - 2 * vn[1:-1, 1:-1] + vn[1:-1, 0:-2]) +
                         dt / dy**2 *
                        (vn[2:, 1:-1] - 2 * vn[1:-1, 1:-1] + vn[0:-2, 1:-1])))

        # Periodic BC in x-direction @ x = 2 (right edge)
        u[1:-1, -1] = (un[1:-1, -1] - un[1:-1, -1] * dt / dx *
                      (un[1:-1, -1] - un[1:-1, -2]) -
                       vn[1:-1, -1] * dt / dy *
                      (un[1:-1, -1] - un[0:-2, -1]) -
                       dt / (2 * rho * dx) *
                      (p[1:-1, 0] - p[1:-1, -2]) +
                       nu * (dt / dx**2 *
                      (un[1:-1, 0] - 2 * un[1:-1,-1] + un[1:-1, -2]) +
                       dt / dy**2 *
                      (un[2:, -1] - 2 * un[1:-1, -1] + un[0:-2, -1])) + F * dt)

        # Periodic BC in x-direction @ x = 0 (left edge)
        u[1:-1, 0] = (un[1:-1, 0] - un[1:-1, 0] * dt / dx *
                     (un[1:-1, 0] - un[1:-1, -1]) -
                      vn[1:-1, 0] * dt / dy *
                     (un[1:-1, 0] - un[0:-2, 0]) -
                      dt / (2 * rho * dx) *
                     (p[1:-1, 1] - p[1:-1, -1]) +
                      nu * (dt / dx**2 *
                     (un[1:-1, 1] - 2 * un[1:-1, 0] + un[1:-1, -1]) +
                      dt / dy**2 *
                     (un[2:, 0] - 2 * un[1:-1, 0] + un[0:-2, 0])) + F * dt)

        v[1:-1, -1] = (vn[1:-1, -1] - un[1:-1, -1] * dt / dx *
                      (vn[1:-1, -1] - vn[1:-1, -2]) -
                       vn[1:-1, -1] * dt / dy *
                      (vn[1:-1, -1] - vn[0:-2, -1]) -
                       dt / (2 * rho * dy) *
                      (p[2:, -1] - p[0:-2, -1]) +
                       nu * (dt / dx**2 *
                      (vn[1:-1, 0] - 2 * vn[1:-1, -1] + vn[1:-1, -2]) +
                       dt / dy**2 *
                      (vn[2:, -1] - 2 * vn[1:-1, -1] + vn[0:-2, -1])))

        v[1:-1, 0] = (vn[1:-1, 0] - un[1:-1, 0] * dt / dx *
                     (vn[1:-1, 0] - vn[1:-1, -1]) -
                      vn[1:-1, 0] * dt / dy *
                     (vn[1:-1, 0] - vn[0:-2, 0]) -
                      dt / (2 * rho * dy) *
                     (p[2:, 0] - p[0:-2, 0]) +
                      nu * (dt / dx**2 *
                     (vn[1:-1, 1] - 2 * vn[1:-1, 0] + vn[1:-1, -1]) +
                      dt / dy**2 *
                     (vn[2:, 0] - 2 * vn[1:-1, 0] + vn[0:-2, 0])))

        # Periodic BC in y-direction @ y = top (wraps to bottom)
        u[-1, 1:-1] = (un[-1, 1:-1] - un[-1, 1:-1] * dt / dx *
                      (un[-1, 1:-1] - un[-1, 0:-2]) -
                       vn[-1, 1:-1] * dt / dy *
                      (un[-1, 1:-1] - un[-2, 1:-1]) -
                       dt / (2 * rho * dx) *
                      (p[-1, 2:] - p[-1, 0:-2]) +
                       nu * (dt / dx**2 *
                      (un[-1, 2:] - 2 * un[-1, 1:-1] + un[-1, 0:-2]) +
                       dt / dy**2 *
                      (un[0, 1:-1] - 2 * un[-1, 1:-1] + un[-2, 1:-1])) + F * dt)

        # Periodic BC in y-direction @ y = bottom (wraps to top)
        u[0, 1:-1] = (un[0, 1:-1] - un[0, 1:-1] * dt / dx *
                     (un[0, 1:-1] - un[0, 0:-2]) -
                      vn[0, 1:-1] * dt / dy *
                     (un[0, 1:-1] - un[-1, 1:-1]) -
                      dt / (2 * rho * dx) *
                     (p[0, 2:] - p[0, 0:-2]) +
                      nu * (dt / dx**2 *
                     (un[0, 2:] - 2 * un[0, 1:-1] + un[0, 0:-2]) +
                      dt / dy**2 *
                     (un[1, 1:-1] - 2 * un[0, 1:-1] + un[-1, 1:-1])) + F * dt)

        v[-1, 1:-1] = (vn[-1, 1:-1] - un[-1, 1:-1] * dt / dx *
                      (vn[-1, 1:-1] - vn[-1, 0:-2]) -
                       vn[-1, 1:-1] * dt / dy *
                      (vn[-1, 1:-1] - vn[-2, 1:-1]) -
                       dt / (2 * rho * dy) *
                      (p[0, 1:-1] - p[-2, 1:-1]) +
                       nu * (dt / dx**2 *
                      (vn[-1, 2:] - 2 * vn[-1, 1:-1] + vn[-1, 0:-2]) +
                       dt / dy**2 *
                      (vn[0, 1:-1] - 2 * vn[-1, 1:-1] + vn[-2, 1:-1])))

        v[0, 1:-1] = (vn[0, 1:-1] - un[0, 1:-1] * dt / dx *
                     (vn[0, 1:-1] - vn[0, 0:-2]) -
                      vn[0, 1:-1] * dt / dy *
                     (vn[0, 1:-1] - vn[-1, 1:-1]) -
                      dt / (2 * rho * dy) *
                     (p[1, 1:-1] - p[-1, 1:-1]) +
                      nu * (dt / dx**2 *
                     (vn[0, 2:] - 2 * vn[0, 1:-1] + vn[0, 0:-2]) +
                      dt / dy**2 *
                     (vn[1, 1:-1] - 2 * vn[0, 1:-1] + vn[-1, 1:-1])))

        # Corner points (periodic in both directions)
        # Top-left corner
        u[0, 0] = (un[0, 0] - un[0, 0] * dt / dx * (un[0, 0] - un[0, -1]) -
                   vn[0, 0] * dt / dy * (un[0, 0] - un[-1, 0]) -
                   dt / (2 * rho * dx) * (p[0, 1] - p[0, -1]) +
                   nu * (dt / dx**2 * (un[0, 1] - 2 * un[0, 0] + un[0, -1]) +
                         dt / dy**2 * (un[1, 0] - 2 * un[0, 0] + un[-1, 0])) + F * dt)

        # Top-right corner
        u[0, -1] = (un[0, -1] - un[0, -1] * dt / dx * (un[0, -1] - un[0, -2]) -
                    vn[0, -1] * dt / dy * (un[0, -1] - un[-1, -1]) -
                    dt / (2 * rho * dx) * (p[0, 0] - p[0, -2]) +
                    nu * (dt / dx**2 * (un[0, 0] - 2 * un[0, -1] + un[0, -2]) +
                          dt / dy**2 * (un[1, -1] - 2 * un[0, -1] + un[-1, -1])) + F * dt)

        # Bottom-left corner
        u[-1, 0] = (un[-1, 0] - un[-1, 0] * dt / dx * (un[-1, 0] - un[-1, -1]) -
                    vn[-1, 0] * dt / dy * (un[-1, 0] - un[-2, 0]) -
                    dt / (2 * rho * dx) * (p[-1, 1] - p[-1, -1]) +
                    nu * (dt / dx**2 * (un[-1, 1] - 2 * un[-1, 0] + un[-1, -1]) +
                          dt / dy**2 * (un[0, 0] - 2 * un[-1, 0] + un[-2, 0])) + F * dt)

        # Bottom-right corner
        u[-1, -1] = (un[-1, -1] - un[-1, -1] * dt / dx * (un[-1, -1] - un[-1, -2]) -
                     vn[-1, -1] * dt / dy * (un[-1, -1] - un[-2, -1]) -
                     dt / (2 * rho * dx) * (p[-1, 0] - p[-1, -2]) +
                     nu * (dt / dx**2 * (un[-1, 0] - 2 * un[-1, -1] + un[-1, -2]) +
                           dt / dy**2 * (un[0, -1] - 2 * un[-1, -1] + un[-2, -1])) + F * dt)

        # Repeat for v velocity corners
        v[0, 0] = (vn[0, 0] - un[0, 0] * dt / dx * (vn[0, 0] - vn[0, -1]) -
                   vn[0, 0] * dt / dy * (vn[0, 0] - vn[-1, 0]) -
                   dt / (2 * rho * dy) * (p[1, 0] - p[-1, 0]) +
                   nu * (dt / dx**2 * (vn[0, 1] - 2 * vn[0, 0] + vn[0, -1]) +
                         dt / dy**2 * (vn[1, 0] - 2 * vn[0, 0] + vn[-1, 0])))

        v[0, -1] = (vn[0, -1] - un[0, -1] * dt / dx * (vn[0, -1] - vn[0, -2]) -
                    vn[0, -1] * dt / dy * (vn[0, -1] - vn[-1, -1]) -
                    dt / (2 * rho * dy) * (p[1, -1] - p[-1, -1]) +
                    nu * (dt / dx**2 * (vn[0, 0] - 2 * vn[0, -1] + vn[0, -2]) +
                          dt / dy**2 * (vn[1, -1] - 2 * vn[0, -1] + vn[-1, -1])))

        v[-1, 0] = (vn[-1, 0] - un[-1, 0] * dt / dx * (vn[-1, 0] - vn[-1, -1]) -
                    vn[-1, 0] * dt / dy * (vn[-1, 0] - vn[-2, 0]) -
                    dt / (2 * rho * dy) * (p[0, 0] - p[-2, 0]) +
                    nu * (dt / dx**2 * (vn[-1, 1] - 2 * vn[-1, 0] + vn[-1, -1]) +
                          dt / dy**2 * (vn[0, 0] - 2 * vn[-1, 0] + vn[-2, 0])))

        v[-1, -1] = (vn[-1, -1] - un[-1, -1] * dt / dx * (vn[-1, -1] - vn[-1, -2]) -
                     vn[-1, -1] * dt / dy * (vn[-1, -1] - vn[-2, -1]) -
                     dt / (2 * rho * dy) * (p[0, -1] - p[-2, -1]) +
                     nu * (dt / dx**2 * (vn[-1, 0] - 2 * vn[-1, -1] + vn[-1, -2]) +
                           dt / dy**2 * (vn[0, -1] - 2 * vn[-1, -1] + vn[-2, -1])))

        udiff = (np.sum(u) - np.sum(un)) / np.sum(u)
        stepcount += 1

    return u, v, p, stepcount


def plot_channel_flow(u, v, X, Y, stride=3, draw=True):
    """Plot velocity field from channel flow solver using quiver plot."""

    fig = plt.figure(figsize=(11, 7), dpi=100)
    plt.quiver(X[::stride, ::stride], Y[::stride, ::stride],
               u[::stride, ::stride], v[::stride, ::stride])
    plt.xlabel('x')
    plt.ylabel('y')
    plt.title('Channel Flow Velocity Field')

    if draw:
        plt.show()

    return fig


if __name__ == '__main__':
    # Run the channel flow solver
    print("Starting channel flow solver...")
    print(f"Grid size: {ny} x {nx}")
    print(f"Physical domain: {Y_LEN} x {X_LEN} m")
    print(f"Time step: {dt} s")

    # Run solver
    u_final, v_final, p_final, steps = channel_flow_solver(
        u.copy(), v.copy(), p.copy(), rho, dt, dx, dy, nu, F
    )

    print(f"Solver converged in {steps} iterations")

    # Unpack meshgrid
    X, Y = GRID

    # Create and save figure
    fig = plot_channel_flow(u_final, v_final, X, Y, stride= 12, draw=False)
    fig.savefig('channel_flow_2.png')
    print("Figure saved as 'channel_flow_2.png'")