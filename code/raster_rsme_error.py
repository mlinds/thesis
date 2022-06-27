import rasterio
from rasterio import warp
import numpy as np
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio import shutil as rio_shutil


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
    return np.nanmean((truth_data_reproj - bilinear_data) ** 2) ** (0.5)


def main():
    print("calculating RMSE with naive interpolation")
    truth_vs_bi = raster_RMSE(
        "../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt",
        "../data/resample_test/bilinear.tif",
    )
    print("calculating RMSE kalman updated bathymetry")
    truth_vs_kalman = raster_RMSE(
        "../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt",
        "../data/resample_test/kalman_updated.tif",
    )
    print(
        {
            "RMSE between truth data and simple bilinear interpolation:": truth_vs_bi,
            "RMSE between truth data and kalman-updated gebco:": truth_vs_kalman,
        }
    )


if __name__ == "__main__":
    main()
