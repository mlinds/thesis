import turtle
import numpy as np
import rasterio
from rasterio import warp
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sklearn.metrics import mean_squared_error
from logzero import setup_logger
from atl_module.geospatial_functions import to_refr_corrected_gdf
from atl_module.raster_interaction import query_raster

import dask.array as da

detail_logger = setup_logger(name="details")
# TODO refactor function names to be more descriptive
# TODO add docstrings to functions


def add_true_elevation(bathy_points, true_data_path, crs):
    gdf = to_refr_corrected_gdf(bathy_points, crs=crs)
    true_bathy = query_raster(
        gdf,
        src=true_data_path,
    )
    # assign the series to the dataframe
    return bathy_points.assign(true_elevation=true_bathy)


def icesat_rmse(bathy_points, true_data_path, crs):
    bathy_points = add_true_elevation(
        bathy_points=bathy_points, true_data_path=true_data_path, crs=crs
    )
    # return the RMS error
    rms = calc_rms_error(bathy_points, ["true_elevation"])
    return rms


def calc_rms_error(beam_df, column_names: list):
    error_dict = {}
    # go over the each DEM, and find the RMS error with the calculated seafloor
    for column in column_names:
        # get a subset of the dataframe that is the seafloor and the column of interest
        comp_columns = beam_df.loc[:, ["z_kde", column]].dropna()
        if len(comp_columns) == 0:
            error_dict[str(column) + "_error"] = np.NaN
        else:
            rms_error = mean_squared_error(
                comp_columns.loc[:, column], comp_columns.loc[:, "z_kde"]
            )
            error_dict[str(column) + "_error"] = rms_error

    return error_dict


import pathlib


def raster_RMSE(truth_raster_path, measured_rasterpath):
    # open the truth raster, which might be in a different crs than the output than the one being compared
    with rasterio.open(truth_raster_path) as truthras:
        truth_raster_crs = truthras.crs
        truth_data_reproj = truthras.read(1, masked=True)
        truth_data_tranform = truthras.transform
    detail_logger.debug(
        f"Opened truth Raster from {truth_raster_path} with CRS {truth_raster_crs.name}"
    )
    # create a band object that will contain the data plus the metadata (crs, etc)
    # truthband = rasterio.band(truthras, 1)

    # open the data to be compared as a rasterio dataset
    measured_ras = rasterio.open(measured_rasterpath)
    detail_logger.debug("opened bilinear raster")
    # going to try to reproject to the same crs as the truth raster to reduce error due to distortion.

    # the next block is actually not required since we don't really need to warp the truth raster

    # First we reproject the truth raster to the same CRS as the kalman update (i.e. )
    # truth_data_reproj, truth_data_tranform = warp.reproject(
    #     truthband, dst_crs=dst_crs, resampling=Resampling.bilinear
    # )
    # # drop the firstlayer of the ndarray
    # truth_data_reproj = truth_data_reproj[0]
    # # mask the NA values from the numpy array
    # truth_data_reproj[(truth_data_reproj == truthras.nodata)] = np.nan

    # get the dimensions we need the output raster to be
    dst_height = truth_data_reproj.shape[0]
    dst_width = truth_data_reproj.shape[1]

    # create an in memory VRT object with the same crs and the same resolution as the truth raster
    # set up the parameters
    vrt_options = {
        "resampling": Resampling.bilinear,
        "crs": truth_raster_crs,
        "transform": truth_data_tranform,
        "height": dst_height,
        "width": dst_width,
        "src_nodata": measured_ras.nodata,
    }
    # actually make the raster
    with WarpedVRT(measured_ras, **vrt_options) as bi_vrt:
        bilinear_data = bi_vrt.read(1, masked=True)
        detail_logger.debug("Warped bilinear gebco interpolation to the truth raster")
        # mask out nodata values

    # with rasterio.open('/mnt/c/Users/XCB/OneDrive - Van Oord/Documents/thesis/data/test_sites/florida_keys/error.tif',mode='w+',crs=dst_crs,transform=truth_data_tranform,height=dst_height,width=dst_width,count=1,dtype=rasterio.float64,nodata=-999999) as errorras:
    #     errorras.write((truth_data_reproj - bilinear_data),1)

    # return the square root of the average of the squared difference
    detail_logger.debug("Calculating rms error")
    errordict = {
        "RMSE": np.nanmean((truth_data_reproj - bilinear_data) ** 2) ** (0.5),
        "MAE": np.nanmean(np.abs(truth_data_reproj - bilinear_data)),
    }
    measured_ras.close()
    return errordict


def main():
    detail_logger.debug("calculating RMSE with naive interpolation")
    truth_vs_bi = raster_RMSE(
        "../data/test_sites/florida_keys/in-situ-DEM/truth.vrt",
        "../data/test_sites/florida_keys/bilinear.tif",
    )
    # print("calculating RMSE kalman updated bathymetry")
    # truth_vs_kalman = raster_RMSE(
    #     "../data/test_sites/florida_keys/in-situ-DEM/truth.vrt",
    #     "../data/resample_test/kalman_updated.tif",
    # )
    print(
        {
            "RMSE between truth data and simple bilinear interpolation:": truth_vs_bi,
            # "RMSE between truth data and kalman-updated gebco:": truth_vs_kalman,
        }
    )


if __name__ == "__main__":
    main()
