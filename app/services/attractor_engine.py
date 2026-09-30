from typing import Any
import numpy as np


class AttractorEngine:
    def __init__(self, attractor_type: str = "clifford", num_points: int = 50000):
        self.attractor_type = attractor_type
        self.num_points = num_points

        self.width = 800
        self.height = 500

        self._set_default_params()
        self._generate_attractor()

    def _set_default_params(self):
        if self.attractor_type == "clifford":
            self.a = -1.4
            self.b = 1.6
            self.c = 1.0
            self.d = 0.7

        elif self.attractor_type == "dejong":
            self.a = -2.2
            self.b = 1.0
            self.c = -2.0
            self.d = 1.8

        elif self.attractor_type == "aizawa":
            self.a = 0.95
            self.b = 0.70
            self.c = 0.60
            self.d = 3.50
            self.e = 0.25
            self.f = 0.10

        elif self.attractor_type == "lorenz":
            self.sigma = 10.0
            self.rho = 28.0
            self.beta = 8.0 / 3.0

    def _next_point(self, x: float, y: float):
        if self.attractor_type == "clifford":
            x_next = np.sin(self.a * y) + self.c * np.cos(self.a * x)
            y_next = np.sin(self.b * x) + self.d * np.cos(self.b * y)

        elif self.attractor_type == "dejong":
            x_next = np.sin(self.a * y) - np.cos(self.b * x)
            y_next = np.sin(self.c * x) - np.cos(self.d * y)

        else:
            x_next = x
            y_next = y

        return x_next, y_next

    def _aizawa_derivatives(self, state: np.ndarray):
        x, y, z = state

        dx = (
            (z - self.b) * x
            - self.d * y
        )

        dy = (
            self.d * x
            + (z - self.b) * y
        )

        dz = (
            self.c
            + self.a * z
            - (z ** 3) / 3.0
            - (x ** 2 + y ** 2) * (1.0 + self.e * z)
            + self.f * z * (x ** 3)
        )

        return np.array([dx, dy, dz], dtype=np.float64)

    def _lorenz_derivatives(self, state: np.ndarray):
        x, y, z = state

        dx = self.sigma * (y - x)
        dy = x * (self.rho - z) - y
        dz = x * y - self.beta * z

        return np.array([dx, dy, dz], dtype=np.float64)

    def _rk4_step(self, state: np.ndarray, dt: float):
        if self.attractor_type == "aizawa":
            derivative = self._aizawa_derivatives
        elif self.attractor_type == "lorenz":
            derivative = self._lorenz_derivatives
        else:
            return state

        k1 = derivative(state)
        k2 = derivative(state + 0.5 * dt * k1)
        k3 = derivative(state + 0.5 * dt * k2)
        k4 = derivative(state + dt * k3)

        return state + (dt / 6.0) * (
            k1 + 2.0 * k2 + 2.0 * k3 + k4
        )

    def _generate_2d_attractor(self):
        x = 0.0
        y = 0.0

        # Discard the initial transient.
        for _ in range(1000):
            x, y = self._next_point(x, y)

        points = np.empty((self.num_points, 2), dtype=np.float64)

        # Generate the actual attractor trajectory.
        for i in range(self.num_points):
            x, y = self._next_point(x, y)
            points[i, 0] = x
            points[i, 1] = y

        self.points = points
        self.x = x
        self.y = y

    def _generate_3d_attractor(self):
        if self.attractor_type == "aizawa":
            # Standard starting position for the Aizawa system.
            state = np.array([0.1, 0.0, 0.0], dtype=np.float64)
            dt = 0.01

        elif self.attractor_type == "lorenz":
            # Standard starting position for the Lorenz system.
            state = np.array([1.0, 1.0, 1.0], dtype=np.float64)
            dt = 0.005

        else:
            return

        # Discard the initial transient.
        for _ in range(5000):
            state = self._rk4_step(state, dt)

        points = np.empty((self.num_points, 3), dtype=np.float64)

        # Generate the actual attractor trajectory.
        for i in range(self.num_points):
            state = self._rk4_step(state, dt)
            points[i] = state

        self.points = points
        self.x = state[0]
        self.y = state[1]
        self.z = state[2]

    def _generate_attractor(self):
        if self.attractor_type in ("clifford", "dejong"):
            self._generate_2d_attractor()

        elif self.attractor_type in ("aizawa", "lorenz"):
            self._generate_3d_attractor()

    def update(self, new_config: dict[str, Any] | None = None):
        params_changed = False

        if new_config:
            if (
                "attractor_type" in new_config
                and new_config["attractor_type"] != self.attractor_type
            ):
                self.attractor_type = new_config["attractor_type"]
                self._set_default_params()
                params_changed = True

            if self.attractor_type in ("clifford", "dejong"):
                parameter_keys = ["a", "b", "c", "d"]

            elif self.attractor_type == "aizawa":
                parameter_keys = ["a", "b", "c", "d", "e", "f"]

            elif self.attractor_type == "lorenz":
                parameter_keys = ["sigma", "rho", "beta"]

            else:
                parameter_keys = []

            for key in parameter_keys:
                if key in new_config:
                    try:
                        new_val = float(new_config[key])

                        if getattr(self, key) != new_val:
                            setattr(self, key, new_val)
                            params_changed = True

                    except (ValueError, TypeError):
                        pass

        if params_changed:
            print(
                "ATTRACTOR UPDATE:",
                self.attractor_type,
                {
                    key: getattr(self, key)
                    for key in (
                        ["a", "b", "c", "d"]
                        if self.attractor_type in ("clifford", "dejong")
                        else ["a", "b", "c", "d", "e", "f"]
                        if self.attractor_type == "aizawa"
                        else ["sigma", "rho", "beta"]
                    )
                }
            )

            self._generate_attractor()

    def get_serialized_state(self):
        return self.points.tolist()