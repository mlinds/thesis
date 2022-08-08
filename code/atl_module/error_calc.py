from os import path

import dask.array as da
import numpy as np
import rasterio
from atl_module.geospatial_utils.geospatial_functions import to_refr_corrected_gdf
from atl_module.geospatial_utils.raster_interaction import query_raster
from logzero import setup_logger
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import get_data_window
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    median_absolute_error,
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
    # the function below needs
    bathy_points = bathy_points.loc[:, ["sf_elev_MSL", "true_elevation"]].dropna()
    # return the RMS error
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


def icesat_error_rms_mae(beam_df):
    # TODO could be deleted, might not be needed
    error_dict = {}
    # go over the each DEM, and find the RMS error with the calculated seafloor
    # get a subset of the dataframe that is the seafloor and the column of interest
    rms_error = icesat_rmse(beam_df)
    mae_error = icesat_mae(beam_df)
    mape = icesat_mape(beam_df)
    med_abs = icesat_med_abs_error(beam_df)
    error_dict["MAE"] = mae_error
    error_dict["RMSE"] = rms_error
    error_dict["MAPE"] = mape
    error_dict["Median Abs error"] = med_abs

    return error_dict


def raster_RMSE_blocked(
    truth_raster_path: str, measured_rasterpath: str, error_out=False
) -> dict:
    """Create a dictionary summarizing the error metrics between two rasters. The measured raster is projected into the same CRS and resolution as the truth raster, and then the RMSE and MAE area calculated.

    This function will perform the function for each GDAL block within the truth raster, which will significantly decrease the memory footprint of the function at the expense of increasing i/o

    Args:
        truth_raster_path (str): The path of the truth raster
        measured_rasterpath (str): the path of the measurement raster, which will be reprojected to the same grid as the truth raster
        error_out (bool, optional): if set to True, the error raster will be written to a separate file. This operation will increase the io load significantly. Defaults to False.

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
        # set up empty to store the mean sqaured error and the mean absolute error
        out_ms = []
        out_mae = []
        # if error output is requested, set up an empty geotiff raster to hold the output
        if error_out:
            folder = path.dirname(measured_rasterpath)
            outpath = path.join(folder, "error_out.tif")
            print(folder, outpath)
            # raise NotImplementedError("fix this function before use")
            out_options = truthras.meta
            # have to remove the driver option so we can write a tif
            out_options.pop("driver")
            outras = rasterio.open(
                outpath,
                mode="w+",
                **out_options,
                compress="lzw",
            )
        # iterate over the blocks in the truth raster
        # if the block contains no data in either of the rasters, the result of the operation will be np.nan
        for ji, window in truthras.block_windows(1):
            # read the truth data by the window and fill the masked values with nans
            truth_data = truthras.read(1, masked=True, window=window)
            truth_data = np.ma.filled(truth_data, np.nan)

            # don't look on land
            truth_data[truth_data > 1] = np.nan

            # count how many non-nan values are in the block.
            # If there are 0 non-nan values, skip it.
            if np.count_nonzero(~np.isnan(truth_data)) == 0:
                continue

            # read the measured data by window
            bilinear_data = bi_vrt.read(1, masked=True, window=window)
            bilinear_data = np.ma.filled(bilinear_data, np.nan)
            error_data = truth_data - bilinear_data
            # if requested, write the error data do a new file
            if error_out:
                outras.write(error_data, window=window, indexes=1)
            # get the mean squared error of the block
            mse = np.nanmean(error_data**2)
            # get the mean absolute error
            mae = np.nanmean(np.abs(error_data))
            out_ms.append(mse)
            out_mae.append(mae)

    errordict = {
        # get the average the average mean sqaured errors and get the root of it
        "RMSE": np.nanmean(out_ms) ** (0.5),
        "MAE": np.nanmean(out_mae),
    }

    return errordict


def raster_RMSE(truth_raster_path, measured_rasterpath):
    # open the truth raster, which might be in a different crs than the output than the one being compared
    with rasterio.open(truth_raster_path) as truthras:
        truth_raster_crs = truthras.crs
        truth_data = truthras.read(1, masked=True)
        # get the window after the data is loaded
        truth_data_window = get_data_window(truth_data)
        # get the new truthdata window
        # TODO loading this twice is too slow
        # truth_data = truthras.read(1, masked=True,window=truth_data_window)
        truth_raster_transform = truthras.transform
    detail_logger.debug(
        f"Opened truth Raster from {truth_raster_path} with CRS {truth_raster_crs}"
    )

    # open the data to be compared as a rasterio dataset
    measured_ras = rasterio.open(measured_rasterpath)
    detail_logger.debug(f"Opened measured raster from {measured_rasterpath}")
    # going to try to reproject to the same crs as the truth raster to reduce error due to distortion.

    # get the dimensions we need the output raster to be
    dst_height = truth_data.shape[0]
    dst_width = truth_data.shape[1]

    # the above might be wrong
    # dst_transform, dst_height, dst_width = warp.calculate_default_transform(
    #     src_crs=measured_ras.crs,
    #     dst_crs=truth_raster_crs,
    #     width=measured_ras.width,
    #     height=measured_ras.height,
    #     resolution=truthras.res,
    #     left=measured_ras.bounds.left,
    #     right=measured_ras.bounds.right,
    #     top=measured_ras.bounds.top,
    #     bottom=measured_ras.bounds.bottom,
    # )

    # create an in memory VRT object with the same crs and the same resolution as the truth raster
    # set up the parameters
    vrt_options = {
        "resampling": Resampling.bilinear,
        "crs": truth_raster_crs,
        "transform": truth_raster_transform,
        "height": dst_height,
        "width": dst_width,
        # "resolution":truthras.res,
        "src_nodata": measured_ras.nodata,
    }
    # actually make the raster
    with WarpedVRT(measured_ras, **vrt_options) as bi_vrt:
        dst_window = bi_vrt.window(
            left=truthras.bounds.left,
            right=truthras.bounds.right,
            bottom=truthras.bounds.bottom,
            top=truthras.bounds.top,
        )
        # for ji,window in bi_vrt.block_windows(1):

        bilinear_data = bi_vrt.read(1, masked=True, window=dst_window)
        bilinear_data = np.ma.filled(bilinear_data, np.nan)
        detail_logger.debug(f"{bilinear_data.nbytes} bytes in reprojected bilinear array")
        detail_logger.debug(f"Interpolated raster shape is {bilinear_data.shape}")
        detail_logger.debug("Warped bilinear gebco interpolation to the truth raster")
        # mask out nodata values

    # return the square root of the average of the squared difference
    detail_logger.debug(f"{truth_data.nbytes} bytes in truth_array")
    detail_logger.debug("Calculating rms error")

    errordict = {
        "RMSE": np.nanmean((truth_data - bilinear_data) ** 2) ** (0.5),
        "MAE": np.nanmean(np.abs(truth_data - bilinear_data)),
    }
    measured_ras.close()

    return errordict


def main(truth, measured):
    print("block verson", raster_RMSE_blocked(truth, measured))
    print("original version", raster_RMSE(truth, measured))


if __name__ == "__main__":
    # import argparse
    # parser = argparse.ArgumentParser()
    # parser.add_argument('truth',type=str)
    # parser.add_argument('measured',type=str)
    # args = parser.parse_args()
    # # print(args.truth)
    main(
        "./data/test_sites/oahu/in-situ-DEM/Job751453_usace2013_oahu_lmsl_dem_000_001.tif",
        "./data/test_sites/oahu/bilinear.tif",
    )
