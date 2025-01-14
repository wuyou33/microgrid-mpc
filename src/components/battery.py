import numpy as np
import pandas as pd

from casadi import SX, Function, vertcat


class Battery:
    def __init__(self, T, N, x_initial, nb, C_MAX):

        self.xk_sim = x_initial
        self.xk_opt = x_initial
        self.nb = nb
        self.C_MAX = C_MAX

        self.T = T
        self.N = N

        self.x = SX.sym("x")
        self.u = SX.sym("u", 2)

        self.ode = (1 / self.C_MAX) * (self.nb * self.u[0] - self.u[1] / self.nb)
        self.F = self.create_integrator()

        self.x_opt = [x_initial]
        self.x_sim = [x_initial]

    def create_integrator(self):

        M = 4
        DT = self.T / self.N / M
        f = Function("f", [self.x, self.u], [self.ode])
        X0 = SX.sym("X0")
        U = SX.sym("U", 2)
        X = X0
        for _ in range(M):
            k1 = f(X, U)
            k2 = f(X + DT / 2 * k1, U)
            k3 = f(X + DT / 2 * k2, U)
            k4 = f(X + DT * k3, U)
            X = X + DT / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        return Function("F", [X0, U], [X], ["x0", "p"], ["xf"])

    def simulate_SOC(self, x, uk):
        """
        Returns the simulated SOC
        """
        Fk = self.F(x0=x, p=uk)
        self.xk_sim = Fk["xf"].full().flatten()[0]

        self.x_opt.append(x)
        self.xk_opt = x
        self.x_sim.append(self.xk_sim)

    def get_SOC(self, openloop):
        if openloop:
            return self.xk_opt
        else:
            return self.xk_sim