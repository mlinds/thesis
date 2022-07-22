import numpy as np
import rasterio
from logzero import setup_logger
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sklearn.metrics import mean_squared_error

from atl_module.geospatial_utils.geospatial_functions import to_refr_corrected_gdf
from atl_module.geospatial_utils.raster_interaction import query_raster
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


def icesat_rmse(bathy_points):
    # the function below needs 
    bathy_points = bathy_points.loc[:,['z_kde','true_elevation']].dropna()
    # return the RMS error
    rms = mean_squared_error(bathy_points.z_kde, bathy_points.true_elevation)
    return rms

# def detailed_lidar_rmse(beam_df):
#     beam_df


def calc_rms_error(beam_df):
    error_dict = {}
    # go over the each DEM, and find the RMS error with the calculated seafloor
    # get a subset of the dataframe that is the seafloor and the column of interest

    rms_error = icesat_rmse(beam_df)

    error_dict["MAE"] = beam_df.eval("error=abs(k_zde-true_elevation)").error.mean()
    error_dict["RMSE"] = rms_error

    return error_dict


def raster_RMSE(truth_raster_path, measured_rasterpath):
    # TODO change to rioxarray
    # open the truth raster, which might be in a different crs than the output than the one being compared
    with rasterio.open(truth_raster_path) as truthras:
        truth_raster_crs = truthras.crs
        truth_data = truthras.read(1, masked=True)
        truth_raster_transform = truthras.transform
    detail_logger.debug(f"Opened truth Raster from {truth_raster_path} with CRS {truth_raster_crs}")

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
    # TODO 
    with WarpedVRT(measured_ras, **vrt_options) as bi_vrt:
        dst_window = bi_vrt.window(
            left=truthras.bounds.left,
            right=truthras.bounds.right,
            bottom=truthras.bounds.bottom,
            top=truthras.bounds.top,
        )

        bilinear_data = bi_vrt.read(1, masked=True, window=dst_window)
        bilinear_data = np.ma.filled(bilinear_data, np.nan)
        detail_logger.debug(f"{bilinear_data.nbytes} bytes in reprojected bilinear array")
        detail_logger.debug(f"Interpolated raster shape is {bilinear_data.shape}")
        detail_logger.debug("Warped bilinear gebco interpolation to the truth raster")
        # mask out nodata values

    # with rasterio.open(
    #     "/mnt/c/Users/maxli/OneDrive - Van Oord/Documents/thesis/data/test_sites/oahu/bilinear_reproj.tif",
    #     compress="lzw",
    #     mode="w+",
    #     crs=truth_raster_crs,
    #     transform=truth_raster_transform,
    #     height=dst_height,
    #     width=dst_width,
    #     count=1,
    #     dtype=rasterio.float32,
    #     nodata=-999999,
    # ) as errorras:
    #     errorras.write(bilinear_data, 1)

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
    raster_RMSE(truth, measured)


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
