import cmocean
import colorcet
import contextily as cx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib_scalebar.scalebar import ScaleBar
from pyproj import Proj
from pyproj import transform as point_transform
from rasterio.plot import show as rastershow

cx.set_cache_dir("/tmp/contextilycache")
LATEX_PAGE_WIDTH = 448.1309


def error_lidar_pt_vs_truth_pt(df_in: pd.DataFrame, error_dict, fraction=0.5):
    fig, ax = plt.subplots(figsize=set_size(ratio=1, fraction=fraction))
    df_in.plot.scatter(
        x="true_elevation",
        y="sf_elev_MSL",
        xlabel="True Elevation [m +MSL]",
        ylabel="Calculated Elevation [m +MSL]",
        # title=f"Lidar Point Vs. Truth Point: {site_name}",
        # bias plots need to be square
        alpha=0.3,
        s=3,
        rasterized=True,
        ax=ax,
    )

    one_to_one_ln_st = min(df_in.true_elevation.min(), df_in.sf_elev_MSL.min())
    one_to_one_ln_end = max(df_in.true_elevation.max(), df_in.sf_elev_MSL.max())
    ax.plot(
        (one_to_one_ln_st, one_to_one_ln_end),
        (one_to_one_ln_st, one_to_one_ln_end),
        c="red",
        label="1=1",
    )
    ax.text(0.05, 0.8, s=f'$RMSE = {error_dict["RMSE"]:.2f}m$', transform=ax.transAxes)
    ax.text(0.05, 0.7, s=f'$R^2 = {error_dict["R2 Score"]:.2f}$', transform=ax.transAxes)
    # ax.text('MAE')
    ax.legend()

    return fig


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


def plot_photon_map(bathy_points_gdf, fraction, figsize=None, colorbar_orient_in=None):
    # get the ratio of the map edges to each other
    minx, miny, maxx, maxy = bathy_points_gdf.total_bounds
    # this ratio we can feed into the figure sizing function
    scale_ratio = (maxx - minx) / (maxy - miny)
    width, height = set_size(fraction=fraction, ratio=scale_ratio)
    colorbar_orient = "vertical"
    # colorbar_fraction = 0.047 * (height / width)
    # if it is too tall for the page, shrink the vertical dimension a bit
    if height > 9:
        scale_relative_to_v = height / 9
        # recalculate so that the vertial side is 9
        width = width / scale_relative_to_v
        height = height / scale_relative_to_v
    # if the map is horizontal, then set the colorbar to be on the long side
    if width > height:
        colorbar_orient = "horizontal"
        # colorbar_fraction = 0.047 * (width / height)
    if colorbar_orient_in is not None:
        colorbar_orient = colorbar_orient_in
    print("Calculated figsize is ", width, height)
    # overide the defaults
    if figsize is not None:
        width, height = figsize
        print("default fig size overwritten with ", width, height)

    icesat_points_figure, ax = plt.subplots(figsize=(width, height))

    print("plotting photon map")
    # pandas plot onto a dataframe returns the artist which we will keep for later
    bathy_points_gdf.plot(
        column="sf_elev_MSL",
        cmap=cmocean.cm.deep_r,
        legend=True,
        legend_kwds={
            "label": "ICESat-2 elevation [m +MSL]",
            "orientation": colorbar_orient,
            #     "fraction": colorbar_fraction,
            "pad": 0.060,
        },
        rasterized=True,
        ax=ax,
        s=1,
    )
    zoom = min(
        13,
        cx.tile._calculate_zoom(*bathy_points_gdf.to_crs("EPSG:4326").geometry.total_bounds),
    )
    cx.add_basemap(
        ax, source=cx.providers.Stamen.TonerLite, crs=bathy_points_gdf.crs, zoom=zoom
    )
    ax.set_xlabel(f"Easting in {bathy_points_gdf.crs.name.strip('WGS 84 / ')}")
    ax.set_ylabel(f"Northing in {bathy_points_gdf.crs.name.strip('WGS 84 / ')}")
    scalebar = ScaleBar(
        1,
        "m",
    )
    ax.add_artist(scalebar)

    # remove contextily attribution which we can add to figure caption
    text = icesat_points_figure.axes[0].texts[0]
    text.set_visible(False)
    text_string_value = text.get_text()
    print("add this to caption! :", text_string_value)
    icesat_points_figure.tight_layout()
    return icesat_points_figure


def plot_tracklines_overview(ax, tracklines_gdf, ratio=0.4, fraction=1.2, figsize_input=None):
    print("plotting tracklines")
    figsize = set_size(ratio=ratio, fraction=fraction)
    print("calculated fig size is", figsize)
    if figsize_input is not None:
        figsize = figsize_input
        print("auto size over written with", figsize)
    tracklines_gdf.plot(figsize=figsize, ax=ax, linewidth=1)
    print("finished plotting tracklines")
    cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, crs=tracklines_gdf.crs)
    print("finished plotting basemap")

    # remove the contextily attribution, which we can add later
    ax.set_xlabel(f"Longitude in {tracklines_gdf.crs.name}")
    ax.set_ylabel(f"Latitude in {tracklines_gdf.crs.name}")
    # ax.set_title("Study site and tracklines")
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
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(5, 3))
    # ax = axes[0]
    # ax.plot(subsurfacedf.delta_time, subsurfacedf.sea_level_interp, label="sea surf")
    # ax.plot(subsurfacedf.delta_time, subsurfacedf.sea_level_interp - 1, label="sea surf - 1m")
    ax.scatter(x=subsurfacedf.delta_time, y=subsurfacedf.Z_refr, s=2, rasterized=True)
    ax.plot(
        bathy_df.delta_time,
        bathy_df.z_kde,
        c="red",
        alpha=0.7,
        label="KDE predicted seafloor",
    )
    ax.plot(
        bathy_df.delta_time,
        bathy_df.true_elevation,
        c="black",
        alpha=0.7,
        label="Actual seafloor",
    )
    ax.set_ylabel("Elevation [m +MSL]")
    ax.legend()
    # add the sea surface
    # ax.axhline(bathy_df.sea_level_interp.iloc[2],c='green')

    # add another axis for the kde
    ax2 = ax.twinx()
    ax2.plot(bathy_df.delta_time, bathy_df.kde_val, c="green")
    ax2.axhline(bathy_df.kde_val.mean(), label="mean kde", c="purple")
    ax2.axhline(bathy_df.kde_val.median(), label="median kde", c="red")
    ax2.plot(bathy_df.delta_time, bathy_df.ph_count, label="ph count")
    ax2.legend(loc="lower right")

    bathy_df = bathy_df.assign(error=bathy_df.true_elevation - bathy_df.z_kde)
    bathy_df = bathy_df.assign(sqerror=bathy_df.error**2)

    time_secs = bathy_df.delta_time.max() - bathy_df.delta_time.min()

    nbins = max(1, int(time_secs.value / 4000000))
    bindf = bathy_df.groupby(pd.cut(bathy_df.delta_time, nbins)).agg(
        {
            "X": "count",
            "sqerror": lambda x: np.power(np.mean(x), 0.5),
            "kde_val": "mean",
        }
    )
    # set ax to be the second subplot
    # ax = axes[1]
    # # plot the error by bin onto the second axis
    # bindf.plot.scatter(y="sqerror", x="kde_val", c="X", cmap="viridis", ax=ax)
    ax.axvline(bindf.kde_val.median(), label="median kde bins")
    ax.axvline(bindf.kde_val.mean(), label="mean kde bins", c="red")
    ax.legend()
    ax.set_title(f"binning with {nbins} bins")

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
    # golden_ratio = (5**0.5 - 1) / 2

    # Figure width in inches
    fig_width_in = fig_width_pt * inches_per_pt

    fig_height_in = fig_width_in / ratio

    fig_dim = (fig_width_in, fig_height_in)

    return fig_dim


def site_overview_map():
    pass


greenredcolormap = colorcet.cm.diverging_gwr_55_95_c38_r


def plot_error_improvement_meters(
    error_raster_path, bathy_points_gdf, figsize=None, cmap_orient=None
):
    """Generate a geospatial plot of the change in the error due to the kalman updating process

    Args:
        error_raster_path (string): path to the raster dataset
        bathy_points_gdf (gpd.GeoDataFrame): bathymetry point geodataframe

    Returns:
        plt.Figure: matplotlib figure object of the geospatial plot
    """
    with rasterio.open(error_raster_path) as error_improvement:
        data = error_improvement.read(1, masked=True)
        data = data.filled(np.NaN)
        transform = error_improvement.transform
        crs = error_improvement.crs
        left, bottom, right, top = error_improvement.bounds
    # the colorbars edges need to be set to show the distribution

    # using the quantiles will show the distribution without being skewed by extreme outliers
    # find the 2% and 98% value
    q2 = np.nanquantile(data, 0.02)
    q98 = np.nanquantile(data, 0.98)
    # get the larger magnitude quantile, then set the high and low based on that
    quantilechoice = max(abs(q2), abs(q98))
    # if not given a figsize argument
    if figsize is None:
        figsize = set_size()

    h, w = data.shape
    if cmap_orient is None:
        if w / h > 1:
            cmap_orient = "horizontal"
        else:
            cmap_orient = "vertical"
    # TODO consider using fancy scalebar options to indicate the true max
    fig, ax = plt.subplots()
    imageartist = ax.imshow(
        data,
        cmap=greenredcolormap,
        vmax=quantilechoice,
        vmin=-1 * quantilechoice,
    )
    fig.colorbar(imageartist, label="Improvement in error [m]", orientation=cmap_orient)
    # clear the axes, so that a version in geospatial coordinates can be created
    ax.clear()
    ax.set_xlim((left, right))
    ax.set_ylim((bottom, top))

    # transform the truth rater coordinates to WGS84 for
    wgs84 = Proj("epsg:4326")
    left_geo, bottom_geo = point_transform(crs, wgs84, left, bottom)
    right_geo, top_geo = point_transform(crs, wgs84, right, top)
    print("original boundaries in truthraster coordinates", left, bottom, right, top)
    print("geographic bounds", left_geo, bottom_geo, right_geo, top_geo)
    # catch when map is overzoomed
    zoom = min(14, cx.tile._calculate_zoom(w=left_geo, e=right_geo, n=top_geo, s=bottom_geo))
    cx.add_basemap(
        ax=ax,
        source=cx.providers.Stamen.TonerLite,
        attribution=False,
        crs=crs,
        zoom=zoom,
    )
    print(transform)
    # actually plot the raster in geospatial coordinates on to the axis
    rastershow(
        data,
        transform=transform,
        cmap=greenredcolormap,
        vmax=quantilechoice,
        vmin=-1 * quantilechoice,
        ax=ax,
    )

    bathy_points_gdf.to_crs(crs).plot(
        ax=ax, label="ICESat-2 points", markersize=0.1, color="black", rasterized=True
    )
    ax.set_xlabel("Longitude WGS84")
    ax.set_ylabel("Latitude WGS84")
    ax.legend()
    return fig


def plot3d(
    subset_pts,
    uncertainty,
    kriged_bathy,
    northings,
    eastings,
    utm_name,
    azim,
    elev,
):
    fig = plt.figure(figsize=set_size(fraction=1, ratio=1))
    ax = plt.axes(projection="3d")
    # set the view, the best view depends on the site so requires experimentation
    ax.view_init(elev=elev, azim=azim)
    ax.scatter3D(
        subset_pts.X,
        subset_pts.Y,
        subset_pts.Z,
        s=3,
        label="ICESat-2 points",
        c="black",
        linewidths=0,
    )
    # set the labels as needed
    ax.set_zlabel("Elevation [m +MSL]")
    ax.set_xlabel(f"Easting [m {utm_name}]")
    ax.set_ylabel(f"Northing [m {utm_name}]")
    fig.tight_layout()

    ax.plot_wireframe(
        eastings,
        northings,
        kriged_bathy,
        color="red",
        alpha=0.5,
        label="Kriging surface",
    )

    # find the location of the bottom of the plot based on the minimum depth of the bathymetry points:
    mindepth = min(subset_pts.Z.min(), kriged_bathy.min())

    ymin = min(subset_pts.Y.min(), northings.min())
    ymax = max(subset_pts.Y.max(), northings.max())
    ax.contourf(
        eastings,
        northings,
        uncertainty,
        100,
        offset=mindepth,
        zdir="z",
        cmap="plasma",
        rasterized=True,
    )
    # contourf_artist.set_rasterized(True)

    # set plot limits
    ax.set_zlim3d(
        top=0,
        bottom=mindepth,
    )
    # ax.set_xlim3d(left=xmin,right=xmax)
    ax.set_ylim3d(top=ymax, bottom=ymin)
    # ax.set_aspect(1.5)

    ax.legend()
    #  commenting out the colorbar for now since it will be displayed next to
    # a figure with the same colorbar
    # fig.colorbar(
    #     contourf_artist,
    #     ax=ax,
    #     label="Variance [m$^2$]",
    #     orientation="vertical",
    #     fraction=0.025,
    #     location="left",
    #     pad=0.01,
    # )

    return fig


def plot_kriging_output(
    kriging_raster_dataset: rasterio.DatasetReader,
    kriging_pt_df,
    uncertainty,
    kriged_bathy,
    horiz=True,
    figsize=None,
    cmap_orient=None,
):
    ncols = 1
    nrows = 2
    if figsize is None:
        figsize = set_size(fraction=1, ratio=1.68 / 1.5)

    if horiz:
        nrows = 1
        ncols = 2
        # figsize = set_size(fraction=1, ratio=1.68 * 2)

    # set up the figure with two subplots
    fig, (ax2, ax1) = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize)
    # get the artists of the imageshow function for later, then clear the axes
    imartist_sigma = ax1.imshow(uncertainty, cmap="plasma")
    ax1.clear()
    imartist_elevation_surface = ax2.imshow(kriged_bathy, cmap=cmocean.cm.deep_r)
    ax2.clear()
    scalebar = ScaleBar(1, units="m", location="lower right")
    ax2.add_artist(scalebar)

    # plot the points on both axes
    kriging_pt_df.plot(ax=ax1, c="black", markersize=2, linewidths=0, label="ICESat-2 Point")
    kriging_pt_df.plot(ax=ax2, c="black", markersize=2, linewidths=0)

    # plot the image with geo unit axes
    rastershow((kriging_raster_dataset, 2), ax=ax1, cmap="plasma")
    rastershow((kriging_raster_dataset, 1), ax=ax2, cmap=cmocean.cm.deep_r)

    if cmap_orient is None:
        # add the colormaps using the artists we got before
        orientval = "vertical"
    else:
        orientval = cmap_orient
    fig.colorbar(
        imartist_sigma,
        ax=ax1,
        label="Variance [m$^2$]",
        orientation=orientval,
        pad=0.05,
    )
    fig.colorbar(
        imartist_elevation_surface,
        ax=ax2,
        label="Interpolated Elevation [m +MSL]",
        orientation=orientval,
        pad=0.05,
    )
    fig.tight_layout()
    return fig


def read_kriging_output(kriging_output_path):
    """Open a raster dataset at a given path and return the relevant variables

    Args:
        kriging_output_path (str): path to a rasterio-readable dataset with 2 bands, where 1 band is the elevation and band 2 is the uncertainty

    Returns:
        tuple: tuple of (uncertinaty_value, elevation_values, easting coordinates, northings coordinates, and the dataset object)
    """
    krigingras = rasterio.open(kriging_output_path)
    # the sigma is the second band
    uncertainty = krigingras.read(2, masked=True).filled(np.NaN)
    # the actual bathymetry estimate is the first band
    kriged_bathy = krigingras.read(1, masked=True).filled(np.NaN)
    height = uncertainty.shape[0]
    width = uncertainty.shape[1]
    cols, rows = np.meshgrid(np.arange(width), np.arange(height))
    xs, ys = rasterio.transform.xy(krigingras.transform, rows, cols)
    eastings = np.array(xs)
    northings = np.array(ys)

    return uncertainty, kriged_bathy, eastings, northings, krigingras
