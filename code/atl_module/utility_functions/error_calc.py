from os import path
from warnings import catch_warnings, simplefilter

import numpy as np
import rasterio
from atl_module.utility_functions.geospatial_functions import to_refr_corrected_gdf
from atl_module.utility_functions.raster_interaction import query_raster
from logzero import setup_logger
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)

detail_logger = setup_logger(name="details")
# TODO add docstrings to functions


def add_true_elevation(bathy_points, true_data_path, crs):
    """takes a bathy points dataframe and add a column called 'true elevation' that contains elevation value of the truth raster at each point

    Args:
        bathy_points (pd.DataFrame): Dataframe of the bathymetryic points, must having X and Y data in the format required
        true_data_path (str): path to a GDAL-readable raster
        crs (str): a string readable by geopandas/prproj that contains the coordinate reference system for the bathymetric points

    Returns:
        pd.Dataframe: the input dataframe with a new column with the true elevation values
    """
    # create a new geodataframe that is updated based on the horizontal error induced by refraction
    gdf = to_refr_corrected_gdf(bathy_points, crs=crs)
    # return a series of the elevation from the truth raster at each point
    true_bathy = query_raster(
        gdf,
        src=true_data_path,
    )
    # assign the series to the dataframe and return
    return bathy_points.assign(true_elevation=true_bathy)


def icesat_rmse(bathy_points):
    """get the RMSE of the bathymetry point dataframe

    Args:
        bathy_points (geopandas.GeoDataFrame): bathymetry point dataframe generated by the module

    Returns:
        float: RMS error
    """
    # the function below needs
    bathy_points = bathy_points.loc[:, ["sf_elev_MSL", "true_elevation"]].dropna()
    # return the RMS error (have to take the root bc the sklearn metrics function only retusn the MSE)
    rms = mean_squared_error(bathy_points.sf_elev_MSL, bathy_points.true_elevation) ** 0.5
    return rms


def icesat_mae(bathy_points):
    # the function below needs
    bathy_points = bathy_points.loc[:, ["sf_elev_MSL", "true_elevation"]].dropna()
    # return the RMS error
    mae = mean_absolute_error(bathy_points.sf_elev_MSL, bathy_points.true_elevation)
    return mae


def icesat_mape(bathy_points):
    # the function below needs
    bathy_points = bathy_points.loc[:, ["sf_elev_MSL", "true_elevation"]].dropna()
    # return the RMS error
    mape = mean_absolute_percentage_error(
        bathy_points.sf_elev_MSL, bathy_points.true_elevation
    )
    return mape


def icesat_med_abs_error(bathy_points):
    # the function below needs
    bathy_points = bathy_points.loc[:, ["sf_elev_MSL", "true_elevation"]].dropna()
    # return the RMS error
    med_abs_error = median_absolute_error(
        bathy_points.sf_elev_MSL, bathy_points.true_elevation
    )
    return med_abs_error


def icesat_r2_score(bathy_points):
    bathy_points = bathy_points.loc[:, ["sf_elev_MSL", "true_elevation"]].dropna()
    # return the RMS error
    r2_score_val = r2_score(bathy_points.sf_elev_MSL, bathy_points.true_elevation)
    return r2_score_val


def icesat_error_metrics(beam_df):
    # TODO could be deleted, might not be needed
    error_dict = {}
    # go over the each DEM, and find the RMS error with the calculated seafloor
    # get a subset of the dataframe that is the seafloor and the column of interest
    error_dict["MAE"] = icesat_mae(beam_df)
    error_dict["RMSE"] = icesat_rmse(beam_df)
    # error_dict["MAPE"] = icesat_mape(beam_df)
    error_dict["Median Abs error"] = icesat_med_abs_error(beam_df)
    error_dict["R2 Score"] = icesat_r2_score(beam_df)
    error_dict["Average Error"] = beam_df.error.mean()

    return error_dict


def raster_RMSE_blocked(
    truth_raster_path: str, measured_rasterpath: str, error_out=None
) -> dict:
    """Create a dictionary summarizing the error metrics between two rasters. The measured raster is projected into the same CRS and resolution as the truth raster, and then the RMSE and MAE area calculated.

    This function will perform the function for each GDAL block within the truth raster, which will significantly decrease the memory footprint of the function at the expense of increasing i/o

    Args:
        truth_raster_path (str): The path of the truth raster
        measured_rasterpath (str): the path of the measurement raster, which will be reprojected to the same grid as the truth raster
        error_out (string, optional): if set to True, the error raster will be written to a separate file. This operation will increase the io load significantly. Defaults to False.

    Returns:
        dict: a dictionary with the keys 'RMSE' and 'MAE', whose values are a float of the respective error value
    """
    measured_ras = rasterio.open(measured_rasterpath)
    # open the truth raster, which might be in a different crs than the output than the one being compared
    with rasterio.open(truth_raster_path) as truthras:
        # get the parameters of the truth raster
        vrt_options = {
            "resampling": Resampling.bilinear,
            "crs": truthras.crs,
            "transform": truthras.transform,
            "height": truthras.height,
            "width": truthras.width,
            "src_nodata": measured_ras.nodata,
        }
        # create a virtual version of the original raster
        bi_vrt = WarpedVRT(measured_ras, **vrt_options)
        # print(' metadata',bi_vrt.meta)
        # set up empty to store the mean sqaured error and the mean absolute error
        out_ms = []
        out_mae = []
        out_me = []
        # if error output is requested, set up an empty geotiff raster to hold the output
        if error_out is not None:
            folder = path.dirname(measured_rasterpath)
            outpath = path.join(folder, error_out)
            print(folder, outpath)
            out_options = truthras.meta
            # have to remove the driver option so we can write a tif
            out_options.pop("driver")
            outras = rasterio.open(
                outpath,
                mode="w+",
                **out_options,
                compress="lzw",
                tiled=True,
                predictor=2,
            )
        # iterate over the blocks in the truth raster
        # if the block contains no data in either of the rasters, the result of the operation will be np.nan
        for ji, block_window in truthras.block_windows(1):
            # read the measured data by window
            bilinear_data = bi_vrt.read(1, masked=True, window=block_window)
            # find the window of valid pixels

            # does the validation data intersect with the estimated data in this block?
            # if not, skip it
            if bilinear_data.count() == 0:
                continue

            # read the truth data by the window and fill the masked values with nans
            truth_data = truthras.read(1, masked=True, window=block_window)
            truth_data = np.ma.filled(truth_data, np.nan)

            # don't look on land
            truth_data[truth_data > 1] = np.nan

            # count how many non-nan values are in the block.
            # If there are 0 non-nan values, skip it.
            if np.count_nonzero(~np.isnan(truth_data)) == 0:
                continue

            bilinear_data = np.ma.filled(bilinear_data, np.nan)
            error_data = truth_data - bilinear_data
            # if requested, write the error data do a new file
            if error_out:
                outras.write(error_data, window=block_window, indexes=1)
            # get the mean squared error of the block
            with catch_warnings():
                simplefilter("ignore", category=RuntimeWarning)
                mse = np.nanmean(error_data**2)
                # get the mean absolute error
                mae = np.nanmean(np.abs(error_data))
                me = np.nanmean(error_data)
            # append the per-block error to the list
            out_ms.append(mse)
            out_mae.append(mae)
            out_me.append(me)

    errordict = {
        # get the average the average mean sqaured errors and get the root of it
        "RMSE [m]": np.nanmean(out_ms) ** (0.5),
        "MAE [m]": np.nanmean(out_mae),
        "Mean Error [m]": np.nanmean(out_me),
    }

    return errordict
