import time
from casadi import *
import matplotlib.pyplot as plt
import utils.plots as p
from utils.helpers import create_logs_folder, parse_config, load_datafile, save_datafile
from simulations.simulate import get_simulations
from open_loop import open_loop_optimization


def main():
    """
    Main function for mpc-scheme with receding horizion.

    Assumptions:
    - Only get weather predicitons at start of interval

    """
    conf = parse_config()

    logpath = None
    log = input("Do you wish to log this run? ")

    if log == "y" or log == "yes" or log == "Yes":
        foldername = input("Do you wish to name logfolder? (enter to skip)")
        logpath = create_logs_folder(conf["logpath"], foldername)

    openloop = input("Run openloop? ")

    actions_per_hour = conf["actions_per_hour"]
    horizon = conf["simulation_horizon"]
    simulation_horizon = horizon * actions_per_hour
    prediction_horizon = conf["prediction_horizon"] * actions_per_hour

    start_time = time.time()
    step_time = start_time

    # Get predictions for time period
    PV, PV_pred, PL, PL_pred, grid_buy, grid_sell = get_simulations(
        actions_per_hour,
        conf["simulation_horizon"],
        conf["simulations"],
        conf["datafile"],
        logpath,
        perfect_predictions=conf["perfect_predictions"],
        plot=conf["plot_predictions"],
    )

    xk = conf["x_inital"]
    x_opt = np.asarray([xk])
    x_sim = np.asarray([xk])
    u0 = np.asarray([])
    u1 = np.asarray([])
    u2 = np.asarray([])
    u3 = np.asarray([])

    for step in range(simulation_horizon):
        if step + prediction_horizon <= simulation_horizon:
            T = prediction_horizon
        else:
            T = simulation_horizon - step
        N = T
        start = step
        stop = np.min([step + prediction_horizon, simulation_horizon])
        xk_sim, u, xk_opt, U_opt = open_loop_optimization(
            xk,
            T,
            N,
            PV[start:stop:],
            PL[start:stop:],
            PV_pred[start:stop:],
            PL_pred[start:stop:],
            **conf["system"],
            plot=False,
            grid_buy=grid_buy[start:stop:],
            grid_sell=grid_sell[start:stop:],
        )

        x_opt = np.append(x_opt, xk_opt[1])
        x_sim = np.append(x_sim, xk_sim)

        if openloop in ["y", "yes", "Yes"]:
            xk = xk_opt[1]  # xk is optimal
        else:
            xk = xk_sim  # xk is simulated difference between measurements and predictions

        # Get the next control actions
        uk = [u[0] for u in U_opt]

        u0 = np.append(u0, uk[0])
        u1 = np.append(u1, uk[1])
        u2 = np.append(u2, uk[2])
        u3 = np.append(u3, uk[3])

        if step % 10 == 0:
            print(
                "\nFinshed iteration step {}. Current step took {}s".format(
                    step, np.around(time.time() - step_time, 2)
                )
            )
            print("xsim {}, x_opt {}".format(xk_sim, xk_opt[1]))
            step_time = time.time()

    # Plotting
    u = np.asarray([-u0, u1, u2, -u3])
    u_bat = np.asarray([-u0, u1])
    u_grid = np.asarray([u2, -u3])

    p.plot_control_actions(u, horizon, actions_per_hour, logpath)

    p.plot_control_actions(
        u_bat,
        horizon,
        actions_per_hour,
        logpath,
        title="Battery actions",
        legends=["Battery Charge", "Battery Discharge"],
    )

    p.plot_control_actions(
        u_grid,
        horizon,
        actions_per_hour,
        logpath,
        title="Grid actions",
        legends=["Grid Buy", "Grid Sell"],
    )

    p.plot_SOC(x_opt, horizon, logpath)
    p.plot_SOC(x_sim, horizon, logpath, title="Simulated State of Charge")

    stop = time.time()
    print("\nFinished optimation in {}s".format(np.around(stop - start_time, 2)))

    save_datafile(
        [x_opt, x_sim, u0, u1, u2, u3, PV, PV_pred, PL, PL_pred],
        names=[
            "x_opt",
            "x_sim",
            "u0",
            "u1",
            "u2",
            "u3",
            "PV",
            "PV_pred",
            "PL",
            "PL_pred",
        ],
        logpath=logpath,
    )
    plt.show()


if __name__ == "__main__":
    main()