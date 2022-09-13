import matplotlib.pyplot as plt
import pandas as pd
import rasterio
from rasterio.plot import show as rastershow


def error_lidar_pt_vs_truth_pt(df_in: pd.DataFrame, site_name, error_dict):
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
    ax.text(0.1, 0.9, s=f'$RMSE = {error_dict["RMSE"]:.2f}m$', transform=ax.transAxes)
    ax.text(0.1, 0.8, s=f'$R^2 = {error_dict["R2 Score"]:.2f}$', transform=ax.transAxes)
    # ax.text(0.2,0.1,f'RMSE = {error_dict['RMSE']}')
    # ax.text('MAE')
    # ax.legend()

    return ax


def map_ground_truth_data(truthdata_path, plottitle):
    # TODO add basemap, currently causing a bug
    with rasterio.open(truthdata_path) as truthraster:
        fig, ax = plt.subplots(figsize=(20, 17))
        ax.set_xlabel(f"Degrees longitude in {truthraster.crs}")
        ax.set_ylabel(f"Degrees latitude in {truthraster.crs}")
        ax.set_title(plottitle)
        image_hidden = ax.imshow(
            truthraster.read(1, masked=True),
            # contour=True,
            cmap="inferno",
        )
        rastershow(
            truthraster,
            cmap="inferno",
            ax=ax,
        )

        fig.colorbar(image_hidden, ax=ax)
        return fig
