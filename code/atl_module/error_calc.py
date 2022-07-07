import numpy as np
import rasterio
from rasterio import warp
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sklearn.metrics import mean_squared_error

from atl_module.geospatial_functions import to_refr_corrected_gdf
from atl_module.raster_interaction import query_raster

import dask.array as da

# TODO refactor function names to be more descriptive
# TODO add docstrings to functions


def add_true_elevation(bathy_points, true_data_path):
    gdf = to_refr_corrected_gdf(bathy_points, crs="EPSG:32617")
    true_bathy = query_raster(
        gdf,
        src=true_data_path,
    )
    # assign the series to the dataframe
    return bathy_points.assign(true_elevation=true_bathy)


def icesat_rmse(bathy_points, true_data_path):
    bathy_points = add_true_elevation(
        bathy_points=bathy_points, true_data_path=true_data_path
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


def raster_RMSE(truth_raster_path, measured_rasterpath):
    # open the truth raster, which might be in a different crs than the output than the one being compared
    truthras = rasterio.open(truth_raster_path)
    # create a band object that will contain the data plus the metadata (crs, etc)
    truthband = rasterio.band(truthras, 1)

    # open the data to be compared as a rasterio dataset
    measured_ras = rasterio.open(measured_rasterpath)

    # going to try to reproject to the same crs as the truth raster to reduce error due to distortion.
    dst_crs = truthras.crs

    # the next block is actually not required since we don't really need to warp the truth raster

    # First we reproject the truth raster to the same CRS as the kalman update (i.e. )
    truth_data_reproj, truth_data_tranform = warp.reproject(
        truthband, dst_crs=dst_crs, resampling=Resampling.bilinear
    )
    # drop the firstlayer of the ndarray
    truth_data_reproj = truth_data_reproj[0]
    # mask the NA values from the numpy array
    truth_data_reproj[(truth_data_reproj == truthras.nodata)] = np.nan

    truth_data_reproj = truthras.read(1, masked=True)
    truth_data_tranform = truthras.transform

    # get the dimensions we need the output raster to be
    dst_height = truth_data_reproj.shape[0]
    dst_width = truth_data_reproj.shape[1]

    # create an in memory VRT object with the same crs and the same resolution as the truth raster
    # set up the parameters
    vrt_options = {
        "resampling": Resampling.bilinear,
        "crs": dst_crs,
        "transform": truth_data_tranform,
        "height": dst_height,
        "width": dst_width,
        "src_nodata": measured_ras.nodata,
    }
    # actually make the raster
    with WarpedVRT(measured_ras, **vrt_options) as bi_vrt:
        bilinear_data = bi_vrt.read(1, masked=True)
        # mask out nodata values

    # return the square root of the average of the squared difference
    errordict = {
        "RMSE": np.nanmean((truth_data_reproj - bilinear_data) ** 2) ** (0.5),
        "MAE": np.nanmean(np.abs(truth_data_reproj - bilinear_data)),
    }
    return errordict


# def main():
#     # print("calculating RMSE with naive interpolation")
#     # truth_vs_bi = raster_RMSE(
#     #     "../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt",
#     #     "../data/resample_test/bilinear.tif",
#     # )
#     print("calculating RMSE kalman updated bathymetry")
#     truth_vs_kalman = raster_RMSE(
#         "../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt",
#         "../data/resample_test/kalman_updated.tif",
#     )
#     print(
#         {
#             # "RMSE between truth data and simple bilinear interpolation:": truth_vs_bi,
#             "RMSE between truth data and kalman-updated gebco:": truth_vs_kalman,
#         }
#     )


# if __name__ == "__main__":
#     main()
