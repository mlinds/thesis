import rasterio
from rasterio import warp
import numpy as np
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio import shutil as rio_shutil

def raster_RMSE(truth_raster_path,measured_rasterpath):
    # open the truth raster, which might be in a different crs than the output than the one being compared
    truthras = rasterio.open(truth_raster_path)
    # create a band object that will contain the data plus the metadata (crs, etc) 
    truthband = rasterio.band(truthras,1)

    # open the data to be compared as a rasterio dataset
    measured_ras = rasterio.open(measured_rasterpath)
    dst_crs = measured_ras.crs

    # First we reproject the truth raster to the same CRS as the kalman update (i.e. )
    fema_projected_array, fema_projected_transform = warp.reproject(truthband,dst_crs=dst_crs,resampling=Resampling.bilinear)
    # drop the firstlayer of the ndarray
    fema_projected_array = fema_projected_array[0]
    # mask the NA values from the numpy array
    fema_projected_array[(fema_projected_array == truthras.nodata)] = np.nan

    # get the dimensions we need the output raster to be
    dst_height = fema_projected_array.shape[0]
    dst_width = fema_projected_array.shape[1]

    # create an in memory VRT object with the same crs and the same resolution as the truth raster 
    vrt_options = {
        'resampling': Resampling.bilinear,
        'crs': dst_crs,
        'transform': fema_projected_transform,
        'height': dst_height,
        'width': dst_width,
        'src_nodata':measured_ras.nodata,
    }
    #
    with WarpedVRT(measured_ras,**vrt_options) as bi_vrt:
        bilinear_data = bi_vrt.read(1)
        # mask out nodata values
        bilinear_data[bilinear_data==measured_ras.nodata] = np.NaN

    return np.nanmean((fema_projected_array-bilinear_data)**2)**(0.5)


def main():
    print('calculating RMSE with naive interpolation')
    truth_vs_bi = raster_RMSE('../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt','../data/resample_test/bilinear.tif')
    print('calculating RMSE kalman updated bathymetry')
    truth_vs_kalman = raster_RMSE('../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt','../data/resample_test/kalman_updated.tif')
    print({'RMSE between truth data and simple bilinear interpolation:':truth_vs_bi,'RMSE between truth data and kalman-updated gebco:':truth_vs_kalman})

if __name__ == "__main__":
    main()
