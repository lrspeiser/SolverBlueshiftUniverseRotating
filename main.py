import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import root_scalar
import logging

# Constants
c = 299792458  # Speed of light in m/s
G = 6.67430e-11  # Gravitational constant
mpc_to_m = 3.0857e22  # Megaparsec to meter conversion
ly_to_m = 9.461e15  # Light year to meter conversion

class RotatingUniverseModel:
    def __init__(self, mass=1e45):
        self.mass = mass
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        self.logger = logging.getLogger(__name__)

    def kerr_metric_components(self, r, omega):
        """Calculate the Kerr metric components for rotating spacetime."""
        try:
            a = omega * r / c  # Angular momentum parameter
            rs = 2 * G * self.mass / (c * c)  # Schwarzschild radius

            # Simplified Kerr metric components in Boyer-Lindquist coordinates
            Delta = r * r - rs * r + a * a
            Sigma = r * r + a * a * np.cos(np.pi/2)**2  # Equatorial plane

            # Metric components
            g_tt = -(1 - rs * r / Sigma)
            g_tphi = -rs * r * a * np.sin(np.pi/2)**2 / Sigma
            g_phiphi = (r * r + a * a + rs * r * a * a * np.sin(np.pi/2)**2 / Sigma) * np.sin(np.pi/2)**2

            return g_tt, g_tphi, g_phiphi
        except Exception as e:
            self.logger.error(f"Error in kerr_metric_components: {e}")
            return None, None, None

    def frame_dragging_frequency(self, r, omega):
        """Calculate frame dragging frequency at radius r."""
        try:
            components = self.kerr_metric_components(r, omega)
            if components[0] is None:
                return 0
            g_tt, g_tphi, g_phiphi = components
            omega_fd = -g_tphi / g_phiphi
            return omega_fd
        except Exception as e:
            self.logger.error(f"Error in frame_dragging_frequency: {e}")
            return 0

    def safe_relativistic_gamma(self, beta):
        """Safely calculate relativistic gamma factor."""
        try:
            if abs(beta) >= 1:
                return float('inf')
            return 1/np.sqrt(1 - beta**2)
        except Exception as e:
            self.logger.error(f"Error in relativistic gamma calculation: {e}")
            return float('inf')

    def coupled_effects(self, r, omega, star_velocity, include_recursion=True):
        """Calculate coupled Doppler and Lense-Thirring effects."""
        try:
            # Base rotation velocity
            v_rot = omega * r

            # Combined velocity (rotation + star motion)
            v_total = v_rot - star_velocity  # Negative for approaching star

            # Initial Doppler calculation
            beta = v_total/c
            if abs(beta) >= 1:
                return None, None, None

            gamma = self.safe_relativistic_gamma(beta)
            doppler = gamma * (1 - beta) - 1

            # Frame dragging effect
            omega_fd = self.frame_dragging_frequency(r, omega)

            # Lense-Thirring calculation
            rel_factor = G * self.mass / (r * c**2)
            base_term = (omega + omega_fd) * r / c
            correction = 1 + 1.5 * rel_factor + 2.25 * rel_factor**2
            lense_thirring = abs(base_term * correction)

            if include_recursion:
                for _ in range(5):
                    v_modified = v_total * (1 + lense_thirring)
                    beta_modified = v_modified/c
                    if abs(beta_modified) >= 1:
                        break

                    gamma_modified = self.safe_relativistic_gamma(beta_modified)
                    doppler = gamma_modified * (1 - beta_modified) - 1
                    correction = 1 + 1.5 * rel_factor * (1 + doppler) + 2.25 * (rel_factor * (1 + doppler))**2
                    lense_thirring = abs(base_term * correction)

            total_shift = doppler + lense_thirring
            return doppler, lense_thirring, total_shift

        except Exception as e:
            self.logger.error(f"Error in coupled_effects: {e}")
            return None, None, None

    def find_required_rotation(self, earth_distance_ly, star_velocity_kms, target_distance_mpc=3.5):
        """Find required universal rotation for given parameters."""
        try:
            earth_distance_m = earth_distance_ly * ly_to_m
            star_velocity_ms = star_velocity_kms * 1000

            def objective(omega):
                results = self.coupled_effects(earth_distance_m, omega, star_velocity_ms)
                if results[0] is None:
                    return float('inf')
                return results[2]  # total shift

            # Binary search with safety checks
            omega_min = 1e-25
            omega_max = 1e-15
            best_omega = None
            min_diff = float('inf')

            for _ in range(50):
                omega = (omega_min + omega_max) / 2
                total = objective(omega)

                if total == float('inf'):
                    omega_max = omega
                    continue

                if abs(total) < min_diff:
                    min_diff = abs(total)
                    best_omega = omega

                if total < 0:
                    omega_min = omega
                else:
                    omega_max = omega

            return best_omega

        except Exception as e:
            self.logger.error(f"Error in find_required_rotation: {e}")
            return None

def analyze_rotation(earth_positions, star_velocity_kms=4000):
    """Analyze required rotation for different Earth positions."""
    model = RotatingUniverseModel()

    print(f"\nAnalyzing Universal Rotation Required to Cancel {star_velocity_kms} km/s Blueshift")
    print("=" * 70)

    for pos_ly in earth_positions:
        print(f"\nEarth at {pos_ly/ly_to_m/1e9:.1f} billion light years from center:")

        omega = model.find_required_rotation(pos_ly/ly_to_m, star_velocity_kms)
        if omega is None:
            print("Could not find valid solution - relativistic limits exceeded")
            continue

        # Calculate rotational effects at different scales
        scales = [
            (1e6, "1 Mpc (Galaxy cluster)"),
            (10e6, "10 Mpc (Local supercluster)"),
            (100e6, "100 Mpc (Large structure)"),
            (1e9, "1 Gpc (Observable universe)")
        ]

        print(f"Angular velocity: {omega:.2e} rad/s")
        print("Rotation speeds at different scales:")

        for ly_radius, name in scales:
            v = omega * (ly_radius * ly_to_m)
            print(f"  {name}: {v/1000:.1f} km/s")

        # Calculate rotation period
        period_years = (2 * np.pi / omega) / (365.25 * 24 * 3600)
        print(f"Complete rotation period: {period_years/1e9:.1f} billion years")

# Test the model with proper scaling
earth_positions = np.array([13e9, 6e9, 3e9]) * ly_to_m  # Convert to meters first
analyze_rotation(earth_positions)