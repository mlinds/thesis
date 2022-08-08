import pandas as pd


def error_lidar_pt_vs_truth_pt(df_in: pd.DataFrame, site_name):
    ax = df_in.plot.scatter(
        x="true_elevation",
        y="z_kde",
        xlabel="True Elevation [m +MSL]",
        ylabel="Calculated Elevation [m +MSL]",
        title=f"Lidar Point Vs. Truth Point: {site_name}",
        figsize=(5, 5),
        alpha=0.3,
    )

    one_to_one_ln_st = min(df_in.true_elevation.min(), df_in.z_kde.min())
    one_to_one_ln_end = max(df_in.true_elevation.max(), df_in.z_kde.max())
    ax.plot(
        (one_to_one_ln_st, one_to_one_ln_end),
        (one_to_one_ln_st, one_to_one_ln_end),
        c="red",
        label="1 = 1",
    )
    ax.legend()
    return ax
