"""
Wing Shape Optimization Module for CFD Analysis
Implements parametric wing generation with multiple interpolation methods
and optimization for lift-to-drag ratio maximization.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline, PchipInterpolator, Akima1DInterpolator, make_interp_spline
from scipy.spatial.distance import cdist
from scipy.optimize import minimize, differential_evolution
import warnings

class Wing:
    """
    Parametric wing shape generator with multiple interpolation methods.
    Defines upper and lower surfaces separately for aerodynamic optimization.
    """

    def __init__(self, chord_length=0.2, n_control_points=5,
                 interpolation_method='pchip', max_thickness=0.15):
        """
        Initialize wing shape generator.

        Parameters:
        -----------
        chord_length : float
            Length of the wing chord (m)
        n_control_points : int
            Number of intermediate control points (hyperparameter to tune)
            Range typically 4-7 for good shape control
        interpolation_method : str
            'cubic_spline', 'pchip', 'akima', 'nurbs_approx'
        max_thickness : float
            Maximum thickness as fraction of chord length (constraint)
        """
        self.chord_length = chord_length
        self.n_control_points = n_control_points
        self.interpolation_method = interpolation_method
        self.max_thickness = max_thickness

        # Wing position in domain
        self.x_start = 0.3  # Start position in domain
        self.y_center = 0.0  # Centerline position

        # Shape parameters (these will be optimized)
        self.upper_heights = None
        self.lower_heights = None

        # Generated wing points
        self.upper_surface = None
        self.lower_surface = None
        self.all_points = None

    def set_shape_parameters(self, upper_heights, lower_heights):
        """
        Set the control point heights for upper and lower surfaces.

        Parameters:
        -----------
        upper_heights : array-like
            Heights of control points for upper surface (positive)
        lower_heights : array-like
            Heights of control points for lower surface (negative)
        """
        self.upper_heights = np.array(upper_heights)
        self.lower_heights = np.array(lower_heights)

        # Enforce constraints
        self._enforce_constraints()

    def _enforce_constraints(self):
        """Apply physical constraints to wing shape."""
        # Upper surface must be positive and below max_thickness
        self.upper_heights = np.clip(self.upper_heights,
                                     0.01 * self.max_thickness,
                                     self.max_thickness)

        # Lower surface must be negative and above -max_thickness
        self.lower_heights = np.clip(self.lower_heights,
                                     -self.max_thickness,
                                     -0.01 * self.max_thickness)

        # Enforce leading and trailing edge to be near zero (thin edges)
        # This is critical for realistic airfoils

    def generate_shape(self, n_points=100):
        """
        Generate wing surface coordinates using selected interpolation method.

        Parameters:
        -----------
        n_points : int
            Number of points to generate on each surface

        Returns:
        --------
        upper_surface, lower_surface : tuple of arrays
            (x, y) coordinates for upper and lower surfaces
        """
        # X positions for control points (distributed along chord)
        # Use cosine spacing for better resolution near leading/trailing edges
        control_x = self._cosine_spacing(self.n_control_points)

        # Add leading edge (0) and trailing edge (1)
        control_x_upper = np.concatenate([[0], control_x, [1]])
        control_x_lower = np.concatenate([[0], control_x, [1]])

        # Heights including leading and trailing edges (both ~0)
        upper_y = np.concatenate([[0.005 * self.max_thickness],
                                  self.upper_heights,
                                  [0.002 * self.max_thickness]])
        lower_y = np.concatenate([[-0.005 * self.max_thickness],
                                  self.lower_heights,
                                  [-0.002 * self.max_thickness]])

        # Generate interpolation points
        x_fine = np.linspace(0, 1, n_points)

        # Apply selected interpolation method
        if self.interpolation_method == 'cubic_spline':
            upper_interpolator = CubicSpline(control_x_upper, upper_y, bc_type='natural')
            lower_interpolator = CubicSpline(control_x_lower, lower_y, bc_type='natural')

        elif self.interpolation_method == 'pchip':
            # PCHIP: Preserves monotonicity, prevents overshooting
            upper_interpolator = PchipInterpolator(control_x_upper, upper_y)
            lower_interpolator = PchipInterpolator(control_x_lower, lower_y)

        elif self.interpolation_method == 'akima':
            # Akima: Less oscillatory than cubic spline
            upper_interpolator = Akima1DInterpolator(control_x_upper, upper_y)
            lower_interpolator = Akima1DInterpolator(control_x_lower, lower_y)

        elif self.interpolation_method == 'nurbs_approx':
            # B-spline approximation (similar to NURBS without weights)
            k = min(3, len(control_x_upper) - 1)  # Spline degree
            upper_interpolator = make_interp_spline(control_x_upper, upper_y, k=k)
            lower_interpolator = make_interp_spline(control_x_lower, lower_y, k=k)
        else:
            raise ValueError(f"Unknown interpolation method: {self.interpolation_method}")

        # Generate surfaces
        y_upper = upper_interpolator(x_fine)
        y_lower = lower_interpolator(x_fine)

        # Convert to absolute coordinates
        x_abs = self.x_start + x_fine * self.chord_length
        y_upper_abs = self.y_center + y_upper
        y_lower_abs = self.y_center + y_lower

        self.upper_surface = np.column_stack([x_abs, y_upper_abs])
        self.lower_surface = np.column_stack([x_abs, y_lower_abs])

        # Combine all points (useful for masking)
        self.all_points = np.vstack([self.upper_surface,
                                     np.flipud(self.lower_surface)])

        return self.upper_surface, self.lower_surface

    def _cosine_spacing(self, n):
        """
        Generate cosine-spaced points between 0 and 1.
        Provides better resolution near leading/trailing edges.
        Excludes endpoints (0 and 1) as they are added separately.
        """
        if n <= 0:
            return np.array([])
        theta = np.linspace(0, np.pi, n + 2)[1:-1]  # Exclude endpoints
        return 0.5 * (1 - np.cos(theta))

    def get_mask(self, X, Y):
        """
        Create boolean mask for points inside the wing.
        Uses point-in-polygon test for arbitrary wing shapes.

        Parameters:
        -----------
        X, Y : 2D arrays
            Meshgrid coordinates of the domain

        Returns:
        --------
        mask : 2D boolean array
            True for points inside wing
        """
        if self.all_points is None:
            raise ValueError("Must call generate_shape() first")

        # Flatten grid points
        points = np.column_stack([X.ravel(), Y.ravel()])

        # Point-in-polygon test using winding number algorithm
        mask_flat = self._points_in_polygon(points, self.all_points)

        return mask_flat.reshape(X.shape)

    def _points_in_polygon(self, points, polygon):
        """
        Test if points are inside a polygon using ray casting.
        """
        from matplotlib.path import Path
        path = Path(polygon)
        return path.contains_points(points)

    def get_boundary_points(self, X, Y, influence_distance=None):
        """
        Find grid points near wing surface for no-slip boundary condition.

        Parameters:
        -----------
        X, Y : 2D arrays
            Meshgrid coordinates
        influence_distance : float
            Distance threshold for boundary influence (default: 2 * grid spacing)

        Returns:
        --------
        boundary_mask : 2D boolean array
            True for points near wing surface
        influence_sections : list of arrays
            For each boundary point, indices of wing surface points influencing it
        """
        if self.all_points is None:
            raise ValueError("Must call generate_shape() first")

        # Estimate grid spacing
        dx = X[0, 1] - X[0, 0]
        dy = Y[1, 0] - Y[0, 0]

        if influence_distance is None:
            influence_distance = 2 * max(dx, dy)

        # Get all grid points
        grid_points = np.column_stack([X.ravel(), Y.ravel()])

        # Compute distances from each grid point to all wing points
        distances = cdist(grid_points, self.all_points)

        # Find nearest wing point for each grid point
        min_distances = np.min(distances, axis=1)
        nearest_wing_idx = np.argmin(distances, axis=1)

        # Boundary points are those within influence_distance of wing
        boundary_mask_flat = min_distances <= influence_distance

        # Exclude points inside the wing
        wing_mask = self.get_mask(X, Y).ravel()
        boundary_mask_flat = boundary_mask_flat & ~wing_mask

        boundary_mask = boundary_mask_flat.reshape(X.shape)

        # For each boundary point, find all wing points within influence distance
        influence_sections = []
        for i, is_boundary in enumerate(boundary_mask_flat):
            if is_boundary:
                # Find all wing points within influence distance
                influenced_by = np.where(distances[i, :] <= influence_distance)[0]
                influence_sections.append(influenced_by)
            else:
                influence_sections.append(np.array([]))

        return boundary_mask, influence_sections

    def apply_no_slip(self, system):
        """
        Apply no-slip boundary condition to the CFD system.

        Parameters:
        -----------
        system : System object
            CFD system from CFD.py
        """
        # Get wing interior mask
        # Note: system.X, system.Y have shape (ny, nx) from meshgrid
        # but system.u, system.v, system.p have shape (nx, ny)
        # So we need to transpose the mask
        wing_mask = self.get_mask(system.X, system.Y)  # Shape: (ny, nx)
        wing_mask_T = wing_mask.T  # Transpose to (nx, ny)

        # Set velocities to zero inside wing
        system.u[wing_mask_T] = 0.0
        system.v[wing_mask_T] = 0.0

        # Get boundary points and apply no-slip
        boundary_mask, _ = self.get_boundary_points(system.X, system.Y)
        boundary_mask_T = boundary_mask.T  # Transpose to match field shape
        system.u[boundary_mask_T] = 0.0
        system.v[boundary_mask_T] = 0.0

    def compute_forces(self, system):
        """
        Compute lift and drag forces on the wing from pressure and viscous forces.

        Parameters:
        -----------
        system : System object
            CFD system after simulation

        Returns:
        --------
        lift : float
            Lift force (N)
        drag : float
            Drag force (N)
        lift_coefficient : float
            Dimensionless lift coefficient
        drag_coefficient : float
            Dimensionless drag coefficient
        """
        if self.all_points is None:
            raise ValueError("Must call generate_shape() first")

        # Get boundary points (returns shape (ny, nx))
        boundary_mask, influence_sections = self.get_boundary_points(system.X, system.Y)
        boundary_mask_T = boundary_mask.T  # Transpose to (nx, ny)

        # Extract pressure and velocity at boundary points
        # Use transposed mask for fields
        boundary_indices_field = np.where(boundary_mask_T)

        # Use original mask for coordinates
        boundary_indices_coord = np.where(boundary_mask)

        if len(boundary_indices_field[0]) == 0:
            return 0.0, 0.0, 0.0, 0.0

        # Pressure forces (normal to surface)
        # system.p has shape (nx, ny), so use transposed indices
        p_boundary = system.p[boundary_indices_field]

        # Compute surface normals (approximate from wing geometry)
        # For each boundary point, find normal direction from nearest wing point
        # system.X, system.Y have shape (ny, nx), so use original indices
        X_boundary = system.X[boundary_indices_coord]
        Y_boundary = system.Y[boundary_indices_coord]

        # Find nearest wing surface points
        boundary_points = np.column_stack([X_boundary, Y_boundary])
        distances = cdist(boundary_points, self.all_points)
        nearest_indices = np.argmin(distances, axis=1)

        # Compute normals (pointing outward from wing)
        normals = np.zeros((len(X_boundary), 2))
        for i, (x, y, wing_idx) in enumerate(zip(X_boundary, Y_boundary, nearest_indices)):
            wing_point = self.all_points[wing_idx]
            # Normal points away from wing
            normal = np.array([x - wing_point[0], y - wing_point[1]])
            norm_length = np.linalg.norm(normal)
            if norm_length > 0:
                normals[i] = normal / norm_length
            else:
                # If exactly on wing, use perpendicular to tangent
                normals[i] = self._compute_normal_at_wing_point(wing_idx)

        # Pressure forces (integrate over surface)
        # F_pressure = -∫ p * n * dS
        dx = system.dx
        dy = system.dy
        dS = np.sqrt(dx**2 + dy**2)  # Approximate surface element

        pressure_forces = -p_boundary[:, np.newaxis] * normals * dS

        # Viscous forces (shear stress from velocity gradients)
        # tau = mu * du/dn (simplified)
        # For now, use simplified viscous drag estimate
        u_boundary = system.u[boundary_indices_field]
        v_boundary = system.v[boundary_indices_field]

        # Total forces
        total_force = np.sum(pressure_forces, axis=0)

        # Decompose into lift (perpendicular to flow) and drag (parallel to flow)
        # Assuming flow is primarily in +x direction
        drag = total_force[0]  # x-component
        lift = total_force[1]  # y-component

        # Compute coefficients
        # C_L = L / (0.5 * rho * U^2 * A)
        # C_D = D / (0.5 * rho * U^2 * A)

        # Reference values
        U_inf = np.mean(system.u[:, 0])  # Freestream velocity (inlet)
        if U_inf == 0:
            U_inf = 1.0  # Default

        A_ref = self.chord_length * 1.0  # Reference area (chord * span, assuming unit span)
        q_inf = 0.5 * system.rho * U_inf**2  # Dynamic pressure

        if q_inf * A_ref > 0:
            lift_coefficient = lift / (q_inf * A_ref)
            drag_coefficient = drag / (q_inf * A_ref)
        else:
            lift_coefficient = 0.0
            drag_coefficient = 0.0

        return lift, drag, lift_coefficient, drag_coefficient

    def _compute_normal_at_wing_point(self, idx):
        """Compute outward normal vector at a wing surface point."""
        n_points = len(self.all_points)

        # Use finite difference to estimate tangent
        if idx == 0:
            tangent = self.all_points[1] - self.all_points[0]
        elif idx == n_points - 1:
            tangent = self.all_points[-1] - self.all_points[-2]
        else:
            tangent = self.all_points[idx+1] - self.all_points[idx-1]

        # Normal is perpendicular to tangent (rotate 90 degrees)
        # For upper surface, normal points up; for lower, points down
        if idx < len(self.upper_surface):
            normal = np.array([-tangent[1], tangent[0]])  # Rotate CCW
        else:
            normal = np.array([tangent[1], -tangent[0]])  # Rotate CW

        # Normalize
        norm_length = np.linalg.norm(normal)
        if norm_length > 0:
            normal = normal / norm_length

        return normal

    def plot_shape(self, ax=None, show_control_points=True):
        """
        Plot the wing shape.

        Parameters:
        -----------
        ax : matplotlib axis (optional)
        show_control_points : bool
            Whether to show control points
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 4))

        if self.upper_surface is None:
            raise ValueError("Must call generate_shape() first")

        # Plot surfaces
        ax.plot(self.upper_surface[:, 0], self.upper_surface[:, 1],
                'b-', linewidth=2, label='Upper surface')
        ax.plot(self.lower_surface[:, 0], self.lower_surface[:, 1],
                'r-', linewidth=2, label='Lower surface')

        # Close the airfoil
        ax.plot([self.upper_surface[-1, 0], self.lower_surface[-1, 0]],
                [self.upper_surface[-1, 1], self.lower_surface[-1, 1]],
                'k-', linewidth=2)
        ax.plot([self.upper_surface[0, 0], self.lower_surface[0, 0]],
                [self.upper_surface[0, 1], self.lower_surface[0, 1]],
                'k-', linewidth=2)

        # Show control points
        if show_control_points:
            control_x = self._cosine_spacing(self.n_control_points)
            x_abs = self.x_start + control_x * self.chord_length
            y_upper = self.y_center + self.upper_heights
            y_lower = self.y_center + self.lower_heights

            ax.plot(x_abs, y_upper, 'bo', markersize=8, label='Upper control points')
            ax.plot(x_abs, y_lower, 'ro', markersize=8, label='Lower control points')

        ax.set_xlabel('x (m)')
        ax.set_ylabel('y (m)')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_title(f'Wing Shape ({self.interpolation_method})')

        return ax


class WingOptimizer:
    """
    Optimization framework for wing shape using CFD simulations.
    Tunes both shape parameters and hyperparameters (number of control points).
    """

    def __init__(self, system, chord_length=0.2, max_thickness=0.15):
        """
        Initialize optimizer.

        Parameters:
        -----------
        system : System object
            CFD system for simulations
        chord_length : float
            Wing chord length (m)
        max_thickness : float
            Maximum allowable thickness
        """
        self.system = system
        self.chord_length = chord_length
        self.max_thickness = max_thickness

        # Optimization history
        self.history = []
        self.best_wing = None
        self.best_L_D_ratio = -np.inf

    def objective_function(self, params, n_control_points, interpolation_method, n_timesteps=50):
        """
        Objective function to minimize (negative lift-to-drag ratio).

        Parameters:
        -----------
        params : array
            Flattened array of [upper_heights, lower_heights]
        n_control_points : int
            Number of control points
        interpolation_method : str
            Interpolation method to use
        n_timesteps : int
            Number of CFD timesteps to simulate

        Returns:
        --------
        objective : float
            Negative L/D ratio (we minimize this)
        """
        # Unpack parameters
        upper_heights = params[:n_control_points]
        lower_heights = params[n_control_points:]

        # Create wing
        wing = Wing(chord_length=self.chord_length,
                   n_control_points=n_control_points,
                   interpolation_method=interpolation_method,
                   max_thickness=self.max_thickness)

        wing.set_shape_parameters(upper_heights, lower_heights)

        try:
            wing.generate_shape()
        except Exception as e:
            print(f"Wing generation failed: {e}")
            return 1e6  # Large penalty

        # Run CFD simulation
        try:
            L, D, C_L, C_D = self._run_simulation(wing, n_timesteps)
        except Exception as e:
            print(f"Simulation failed: {e}")
            return 1e6  # Large penalty

        # Compute L/D ratio
        if D > 1e-10:
            L_D_ratio = L / D
        else:
            L_D_ratio = 0.0

        # We want to maximize L/D, so minimize negative L/D
        objective = -L_D_ratio

        # Add penalties for unrealistic shapes
        # Penalty for excessive thickness variations
        thickness_penalty = np.sum(np.abs(np.diff(upper_heights))) + \
                           np.sum(np.abs(np.diff(lower_heights)))
        objective += 0.01 * thickness_penalty

        # Store in history
        self.history.append({
            'params': params.copy(),
            'n_control_points': n_control_points,
            'interpolation_method': interpolation_method,
            'L': L,
            'D': D,
            'C_L': C_L,
            'C_D': C_D,
            'L_D_ratio': L_D_ratio,
            'objective': objective
        })

        # Update best wing
        if L_D_ratio > self.best_L_D_ratio:
            self.best_L_D_ratio = L_D_ratio
            self.best_wing = wing
            print(f"New best L/D: {L_D_ratio:.3f} (C_L={C_L:.3f}, C_D={C_D:.4f})")

        return objective

    def _run_simulation(self, wing, n_timesteps=50):
        """
        Run CFD simulation with given wing.

        Parameters:
        -----------
        wing : Wing object
        n_timesteps : int
            Number of timesteps

        Returns:
        --------
        L, D, C_L, C_D : tuple
            Lift, drag, and coefficients
        """
        # Reset system to initial conditions
        # Note: System fields have shape (nx, ny)
        self.system.u = np.ones((self.system.nx, self.system.ny)) * 1.0  # Freestream
        self.system.v = np.zeros((self.system.nx, self.system.ny))
        self.system.p = np.zeros((self.system.nx, self.system.ny))

        # Set body forces (constant freestream forcing)
        self.system.Fx = np.ones((self.system.nx, self.system.ny)) * 0.001  # Very small for stability
        self.system.Fy = np.zeros((self.system.nx, self.system.ny))

        # Run time steps
        for step in range(n_timesteps):
            # Pressure solve
            self.system.p, _ = self.system.pressure_step_v2()

            # Momentum update
            self.system.motion_step()

            # Apply wing boundary condition
            wing.apply_no_slip(self.system)

            # Check for divergence
            if np.any(np.isnan(self.system.u)) or np.any(np.isinf(self.system.u)):
                raise ValueError("Simulation diverged")

        # Compute forces
        L, D, C_L, C_D = wing.compute_forces(self.system)

        return L, D, C_L, C_D

    def optimize(self, n_control_points_range=(4, 7),
                 interpolation_methods=['pchip', 'akima', 'cubic_spline'],
                 n_iterations=50, n_timesteps=50):
        """
        Optimize wing shape over hyperparameters and shape parameters.

        Parameters:
        -----------
        n_control_points_range : tuple
            Range of control points to try (min, max)
        interpolation_methods : list
            List of interpolation methods to try
        n_iterations : int
            Number of optimization iterations per configuration
        n_timesteps : int
            CFD timesteps per evaluation

        Returns:
        --------
        best_wing : Wing object
            Optimized wing shape
        """
        print("="*60)
        print("WING SHAPE OPTIMIZATION")
        print("="*60)

        # Grid search over hyperparameters
        for n_cp in range(n_control_points_range[0], n_control_points_range[1] + 1):
            for method in interpolation_methods:
                print(f"\nOptimizing: n_control_points={n_cp}, method={method}")
                print("-"*60)

                # Initialize with NACA-like shape (proven good starting point)
                upper_init = self._naca_like_shape(n_cp, is_upper=True)
                lower_init = self._naca_like_shape(n_cp, is_upper=False)

                x0 = np.concatenate([upper_init, lower_init])

                # Bounds for optimization
                bounds_upper = [(0.01 * self.max_thickness, self.max_thickness)] * n_cp
                bounds_lower = [(-self.max_thickness, -0.01 * self.max_thickness)] * n_cp
                bounds = bounds_upper + bounds_lower

                # Run optimization
                result = differential_evolution(
                    self.objective_function,
                    bounds=bounds,
                    args=(n_cp, method, n_timesteps),
                    maxiter=n_iterations,
                    popsize=10,
                    seed=42,
                    disp=True,
                    workers=1  # Sequential for stability
                )

                print(f"Optimization complete: L/D = {-result.fun:.3f}")

        print("\n" + "="*60)
        print(f"BEST WING FOUND: L/D = {self.best_L_D_ratio:.3f}")
        print("="*60)

        return self.best_wing

    def _naca_like_shape(self, n_points, is_upper=True):
        """
        Generate NACA-like initial guess for optimization.
        Uses NACA 4-digit series as inspiration.
        """
        x = self._cosine_spacing(n_points)

        # NACA 2412-like shape (2% camber, 40% max camber location, 12% thickness)
        t = 0.12 * self.max_thickness  # thickness

        if is_upper:
            # Upper surface (positive)
            y = t * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 +
                     0.2843 * x**3 - 0.1015 * x**4)
            # Add camber
            y += 0.02 * self.max_thickness * (1 - x)
        else:
            # Lower surface (negative)
            y = -t * (0.2969 * np.sqrt(x) - 0.126 * x - 0.3516 * x**2 +
                      0.2843 * x**3 - 0.1015 * x**4)
            # Add camber
            y += 0.02 * self.max_thickness * (1 - x)

        return y

    def _cosine_spacing(self, n):
        """Generate cosine-spaced points."""
        if n <= 0:
            return np.array([])
        theta = np.linspace(0, np.pi, n + 2)[1:-1]
        return 0.5 * (1 - np.cos(theta))

    def plot_optimization_history(self):
        """Plot optimization history showing L/D ratios over iterations."""
        if not self.history:
            print("No optimization history to plot")
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Extract data
        iterations = np.arange(len(self.history))
        L_D_ratios = [h['L_D_ratio'] for h in self.history]
        C_L = [h['C_L'] for h in self.history]
        C_D = [h['C_D'] for h in self.history]

        # Plot L/D ratio
        axes[0, 0].plot(iterations, L_D_ratios, 'b-', alpha=0.6)
        axes[0, 0].plot(iterations, L_D_ratios, 'bo', markersize=3)
        axes[0, 0].set_xlabel('Iteration')
        axes[0, 0].set_ylabel('L/D Ratio')
        axes[0, 0].set_title('Lift-to-Drag Ratio Evolution')
        axes[0, 0].grid(True, alpha=0.3)

        # Plot C_L
        axes[0, 1].plot(iterations, C_L, 'g-', alpha=0.6)
        axes[0, 1].plot(iterations, C_L, 'go', markersize=3)
        axes[0, 1].set_xlabel('Iteration')
        axes[0, 1].set_ylabel('C_L')
        axes[0, 1].set_title('Lift Coefficient')
        axes[0, 1].grid(True, alpha=0.3)

        # Plot C_D
        axes[1, 0].plot(iterations, C_D, 'r-', alpha=0.6)
        axes[1, 0].plot(iterations, C_D, 'ro', markersize=3)
        axes[1, 0].set_xlabel('Iteration')
        axes[1, 0].set_ylabel('C_D')
        axes[1, 0].set_title('Drag Coefficient')
        axes[1, 0].grid(True, alpha=0.3)

        # Plot C_L vs C_D (drag polar)
        axes[1, 1].plot(C_D, C_L, 'b-', alpha=0.6)
        axes[1, 1].plot(C_D, C_L, 'bo', markersize=3)
        axes[1, 1].set_xlabel('C_D')
        axes[1, 1].set_ylabel('C_L')
        axes[1, 1].set_title('Drag Polar')
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        return fig


def compare_interpolation_methods(n_control_points=5, max_thickness=0.15):
    """
    Compare different interpolation methods visually.
    Shows how each method handles the same control points.
    """
    # Sample control points (NACA-like)
    methods = ['cubic_spline', 'pchip', 'akima', 'nurbs_approx']

    # Generate sample heights
    x = np.linspace(0, 1, n_control_points)
    upper_heights = max_thickness * (0.3 * np.sqrt(x) - 0.1 * x - 0.2 * x**2)
    lower_heights = -max_thickness * (0.25 * np.sqrt(x) - 0.08 * x - 0.15 * x**2)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.ravel()

    for idx, method in enumerate(methods):
        wing = Wing(n_control_points=n_control_points,
                   interpolation_method=method,
                   max_thickness=max_thickness)
        wing.set_shape_parameters(upper_heights, lower_heights)
        wing.generate_shape(n_points=150)

        wing.plot_shape(ax=axes[idx], show_control_points=True)

    plt.tight_layout()
    plt.savefig('interpolation_comparison.png', dpi=150, bbox_inches='tight')
    print("Saved comparison plot: interpolation_comparison.png")

    return fig


if __name__ == '__main__':
    # Demonstration: Compare interpolation methods
    print("Comparing interpolation methods...")
    compare_interpolation_methods(n_control_points=5, max_thickness=0.15)

    print("\nWing optimizer module loaded successfully!")
    print("To run optimization, use:")
    print("  from CFD import System")
    print("  from wing_optimizer import WingOptimizer")
    print("  system = System(...)")
    print("  optimizer = WingOptimizer(system)")
    print("  best_wing = optimizer.optimize()")
