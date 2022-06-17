# %%
import numpy as np
import rasterio


def simple_kalman(z, sigma, z_meas, sigma_meas):
    """vectorizable function that does the kalman update step in 1d, saves the results to a tif file

    Args:
        z (float): initial geuss
        sigma (float): uncertainty of initial depth in standard deviation
        z_meas (float): new, measured value
        sigma_meas (float): uncertainty in the measured value in STANDARD DEVIATION

    Returns:
        tuple: new grid of Z and uncertainty
    """
    variance = sigma**2
    variance_meas = sigma_meas**2
    gain = variance / (variance + variance_meas)
    znew = z + gain * (z_meas - z)
    # get the new variance and convert it to a standard deviation
    sigmanew = ((1 - gain) * variance) ** 0.5
    return znew, sigmanew


def do_kalman_update(outputfile, start_raster_path, updateraster):

    # load the results of the interpolation
    gebco_interp = rasterio.open(start_raster_path)
    krige_results = rasterio.open(updateraster)

    gebco_depth = gebco_interp.read(1)
    # set nodata values to numpy Nodata
    gebco_depth[gebco_depth == -3.2767e04] = np.NaN
    kriged_depth = krige_results.read(1)
    # convert variance to std dev
    kriged_std = np.sqrt(krige_results.read(2))
    gebco_uncertainty = np.full_like(gebco_depth, 2)

    # do the kalman update and save the file
    updated_depth_grid, updated_uncertainty_grid = simple_kalman(
        gebco_depth, gebco_uncertainty, kriged_depth, kriged_std
    )

    with rasterio.open(
        outputfile,
        mode="w+",
        crs=gebco_interp.crs,
        width=gebco_interp.width,
        height=gebco_interp.height,
        count=1,
        dtype=gebco_interp.dtypes[0],
        transform=gebco_interp.transform,
    ) as outras:
        outras.write(updated_depth_grid, 1)


if __name__ == "__main__":
    do_kalman_update(
        "../data/resample_test/kalman_updated.tif",
        "../data/resample_test/bilinear.tif",
        "../data/resample_test/interp_OK.tif",
    )
