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


def gridded_kalman_update(outputfile, start_raster_path, measrasterlist):

    # if there is a single path instead of a list, convert it to a single-element list
    if isinstance(measrasterlist, str):
        measrasterlist = [measrasterlist]

    # load the results of the interpolation
    with rasterio.open(start_raster_path) as gebco_interp:
        gebco_depth = gebco_interp.read(1)
    # set nodata values to numpy Nodata
    gebco_depth[gebco_depth == -3.2767e04] = np.NaN
    gebco_uncertainty = np.full_like(gebco_depth, 2)

    # set initial value for first loop
    kalman_depth = gebco_depth
    kalman_uncertainty = gebco_uncertainty

    # loop over
    for measrasterpath in measrasterlist:
        with rasterio.open(measrasterpath) as measurement_raster_file:
            measurement_depths = measurement_raster_file.read(1)
            # convert variance to std dev
            measurement_sigma = np.sqrt(measurement_raster_file.read(2))

        kalman_depth, kalman_uncertainty = simple_kalman(
            kalman_depth, kalman_uncertainty, measurement_depths, measurement_sigma
        )

    # TODO consider abstracting this into another function
    # write the output to a raster file
    with rasterio.open(
        outputfile,
        mode="w+",
        crs=gebco_interp.crs,
        width=gebco_interp.width,
        height=gebco_interp.height,
        count=2,
        dtype=gebco_interp.dtypes[0],
        transform=gebco_interp.transform,
    ) as outras:
        outras.write(kalman_depth, 1)
        outras.write(kalman_uncertainty, 2)

    return None


if __name__ == "__main__":
    gridded_kalman_update(
        "../data/resample_test/kalman_updated.tif",
        "../data/resample_test/bilinear.tif",
        "../data/resample_test/interp_OK.tif",
    )
