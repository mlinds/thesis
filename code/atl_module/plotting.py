import contextily as cx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.plot import show as rastershow

LATEX_PAGE_WIDTH = 448.1309


def error_lidar_pt_vs_truth_pt(df_in: pd.DataFrame, site_name, error_dict):
    ax = df_in.plot.scatter(
        x="true_elevation",
        y="sf_elev_MSL",
        xlabel="True Elevation [m +MSL]",
        ylabel="Calculated Elevation [m +MSL]",
        title=f"Lidar Point Vs. Truth Point: {site_name}",
        figsize=set_size(),
        alpha=0.3,
        s=3,
        rasterized=True,
    )

    one_to_one_ln_st = min(df_in.true_elevation.min(), df_in.sf_elev_MSL.min())
    one_to_one_ln_end = max(df_in.true_elevation.max(), df_in.sf_elev_MSL.max())
    ax.plot(
        (one_to_one_ln_st, one_to_one_ln_end),
        (one_to_one_ln_st, one_to_one_ln_end),
        c="red",
        label="1=1",
    )
    ax.text(0.1, 0.8, s=f'$RMSE = {error_dict["RMSE"]:.2f}m$', transform=ax.transAxes)
    ax.text(0.1, 0.75, s=f'$R^2 = {error_dict["R2 Score"]:.2f}$', transform=ax.transAxes)
    # ax.text('MAE')
    ax.legend()

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


def plot_photon_map(ax, bathy_points_gdf):
    print("plotting photon map")
    bathy_points_gdf.plot(
        figsize=set_size(),
        column="z_kde",
        cmap="inferno",
        legend=True,
        legend_kwds={"label": "Depth estimate using only ICESat-2 [m +MSL]", "shrink": 0.25},
        rasterized=True,
        ax=ax,
        s=4,
    )
    print("finished plotting photons")
    cx.add_basemap(ax, source=cx.providers.OpenTopoMap, crs=bathy_points_gdf.crs)
    print("finished adding basemap")

    # ax.colorbar(ptsartist,fraction=0.046, pad=0.04)

    ax.set_xlabel(f"Easting in {bathy_points_gdf.crs.name}")
    ax.set_ylabel(f"Northing in {bathy_points_gdf.crs.name}")
    ax.set_title("Bathymetric photons identified by rolling-window KDE")
    # return ax


def plot_tracklines_overview(ax, tracklines_gdf):
    print("plotting tracklines")
    tracklines_gdf.plot(figsize=set_size(), ax=ax)
    print("finished plotting tracklines")
    cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, crs=tracklines_gdf.crs)
    print("finished plotting basemap")
    ax.set_xlabel(f"Easting in {tracklines_gdf.crs.name}")
    ax.set_ylabel(f"Northing in {tracklines_gdf.crs.name}")
    ax.set_title("Study site and tracklines")
    # return ax


def plot_aoi(ax, aoi_gdf):
    aoi_gdf.plot(ax=ax, color="red")


def plot_both_maps(tracklines_gdf, bathy_points_gdf, aoi_gdf):

    # this in hacky, but creates to axes, then has functions that modifies the axes objects in place
    fig, (photon_ax, track_ax) = plt.subplots(nrows=2, ncols=1)
    plot_aoi(track_ax, aoi_gdf)
    plot_tracklines_overview(track_ax, tracklines_gdf)
    plot_photon_map(photon_ax, bathy_points_gdf)
    return fig


def plot_transect_results(subsurfacedf, bathy_df, figpath):
    # this could be two or 4 functions :(
    fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(20, 10))
    ax = axes[0]
    ax.plot(subsurfacedf.delta_time, subsurfacedf.sea_level_interp, label="sea surf")
    ax.plot(subsurfacedf.delta_time, subsurfacedf.sea_level_interp - 1, label="sea surf - 1m")
    ax.scatter(x=subsurfacedf.delta_time, y=subsurfacedf.Z_refr, s=4, rasterized=True)
    ax.plot(bathy_df.delta_time, bathy_df.z_kde, c="red", alpha=0.7)
    ax.plot(bathy_df.delta_time, bathy_df.true_elevation, c="black", alpha=0.7)
    ax.legend()
    # add the sea surface
    # ax.axhline(bathy_df.sea_level_interp.iloc[2],c='green')

    # add another axis for the kde
    ax2 = ax.twinx()
    ax2.plot(bathy_df.delta_time, bathy_df.kde_val, c="green")
    ax2.axhline(bathy_df.kde_val.mean(), label="mean kde", c="purple")
    ax2.axhline(bathy_df.kde_val.median(), label="median kde", c="red")
    # ax2.plot(bathy_df.delta_time,bathy_df.ph_count,label='ph count')
    ax2.legend(loc="lower right")

    bathy_df = bathy_df.assign(error=bathy_df.true_elevation - bathy_df.z_kde)
    bathy_df = bathy_df.assign(sqerror=bathy_df.error**2)

    time_secs = bathy_df.delta_time.max() - bathy_df.delta_time.min()

    nbins = max(1, int(time_secs.value / 4000000))
    bindf = bathy_df.groupby(pd.cut(bathy_df.delta_time, nbins)).agg(
        {"X": "count", "sqerror": lambda x: np.power(np.mean(x), 0.5), "kde_val": "mean"}
    )
    # set ax to be the second subplot
    ax = axes[1]
    # plot the error by bin onto the second axis
    bindf.plot.scatter(y="sqerror", x="kde_val", c="X", cmap="viridis", ax=ax)
    ax.axvline(bindf.kde_val.median(), label="median kde bins")
    ax.axvline(bindf.kde_val.mean(), label="mean kde bins", c="red")
    ax.legend()
    ax.set_title(f"binning with {nbins}")

    fig.savefig(figpath, bbox_inches="tight")


def set_size(fraction=1, ratio=1.618):
    """Set figure dimensions to avoid scaling in LaTeX.

    Parameters
    ----------
    width: float
            Document textwidth or columnwidth in pts
    fraction: float, optional
            Fraction of the width which you wish the figure to occupy

    Returns
    -------
    fig_dim: tuple
            Dimensions of figure in inches
    """
    # Width of figure (in pts)
    fig_width_pt = LATEX_PAGE_WIDTH * fraction

    # Convert from pt to inches
    inches_per_pt = 1 / 72.27

    # Golden ratio to set aesthetic figure height
    # https://disq.us/p/2940ij3
    golden_ratio = (5**0.5 - 1) / 2

    # Figure width in inches
    fig_width_in = fig_width_pt * inches_per_pt
    5
    fig_height_in = fig_width_in * golden_ratio

    fig_dim = (fig_width_in, fig_height_in)

    return fig_dim
