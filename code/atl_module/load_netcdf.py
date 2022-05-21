from os import PathLike

import numpy as np
import pandas as pd
from cftime import num2pydate
from netCDF4 import Dataset


beamlist = ["gt1l", "gt1r", "gt2l", "gt2r", "gt3l", "gt3r"]


def get_beams(granule_netcdf: str or PathLike) -> list:
    """List the beams available for a given granule

    Args:
        granule_netcdf (Pathlike): Path to granule NETCDF file

    Returns:
        list: List of beams
    """
    try:
        with Dataset(granule_netcdf) as netcdfdataset:
            return [
                beam
                for beam in netcdfdataset.groups
                if (beam in beamlist)
                and ("heights" in netcdfdataset.groups[beam].groups)
            ]
    # i  know pass in an except block is bad coding but i need to find a better way of handling this
    except AttributeError:
        pass


def load_beam_array_ncds(filename: str or PathLike, beam: str) -> np.ndarray:
    """return an array of photon-level details for a given file and beam name.

    Granule-level metadata is also included with the array
    """
    # this function is a mess and should probably abstracted into smaller functions
    # if the pandas df induces too much overhead, could maybe be rewritten in numpy

    with Dataset(filename) as ds:

        # get the granule-level metadata
        metadata = {
            varname: str(values[:])
            for varname, values in ds.groups["ancillary_data"].variables.items()
        }
        # add the beam-level metadata by looping over attribute names and getting them from the
        # netcdf group
        for attribute_name in ds.groups[beam].ncattrs():
            metadata[attribute_name] = str(getattr(ds.groups[beam], attribute_name))

        try:
            metadata["ocean_high_conf_perc"] = float(
                ds.groups["quality_assessment"]
                .groups[beam]
                .variables["qa_perc_signal_conf_ph_high"][:, 1]
            )
        except KeyError:
            metadata["ocean_high_conf_perc"] = np.NaN

        # this is in a try block because it raises a keyerror if the beam is missing from the granule
        try:
            ds.groups[beam].groups["heights"]

        except KeyError:
            return None
        # get array-type data
        Y = ds.groups[beam].groups["heights"].variables["lat_ph"][:]
        X = ds.groups[beam].groups["heights"].variables["lon_ph"][:]
        Z = ds.groups[beam].groups["heights"].variables["h_ph"][:]

        # based on the data documentation, the dates are referenced to the 2018-01-01 so the
        # datetimes are shifted accordingly
        delta_time_s = ds.groups[beam].groups["heights"].variables["delta_time"][:]
        delta_time = num2pydate(delta_time_s, "seconds since 2018-01-01")

        ocean_sig = ds.groups[beam].groups["heights"].variables["signal_conf_ph"][:, 1]
        land_sig = ds.groups[beam].groups["heights"].variables["signal_conf_ph"][:, 0]

        # need to deal with geophysical variable time differenently since they're captured at a different rate
        delta_time_geophys_s = (
            ds.groups[beam].groups["geophys_corr"].variables["delta_time"][:]
        )
        delta_time_geophys = num2pydate(
            delta_time_geophys_s, "seconds since 2018-01-01"
        )

        # to index these we need to set the first value to the first value of the
        # photon returns. This is because the photon time values start in the middle of a segment

        delta_time_geophys[0] = delta_time[0]

        # get the geophysical variables
        geo_f2m = (
            ds.groups[beam]
            .groups["geophys_corr"]
            .variables["geoid_free2mean"][:]
            .filled(np.NaN)
        )
        geoid = (
            ds.groups[beam].groups["geophys_corr"].variables["geoid"][:].filled(np.NaN)
        )
        tide_ocean = (
            ds.groups[beam]
            .groups["geophys_corr"]
            .variables["tide_ocean"][:]
            .filled(np.NaN)
        )

        # combine the corrections into one
        # this must be subtracted from Z ellipsoidal (see page 3 of data comparison manual v005)
        correction = geoid + geo_f2m + tide_ocean

        # to assign the correct correction value, we need to get the correction at a certain time
        # to do this we can align them using the pandas asof

        # switch into pandas to use as_of function
        zcorr_series = pd.Series(correction, index=delta_time_geophys).sort_index()

        # make an array of the correction by time
        z_corr = zcorr_series.asof(delta_time).to_numpy()

        # get the corrected Z vals
        Z_corrected = Z - z_corr

        # for varname, values in (
        #     ds.groups["quality_assessment"].groups[beam].variables.items()
        # ):
        #     metadata[varname + "_ocean"] = values[:].data[0][1]
        #     metadata[varname + "_land"] = values[:].data[0][0]

        # creating a structured array

        dtype = np.dtype(
            [
                ("X", "<f8"),
                ("Y", "<f8"),
                ("Z", "<f8"),
                ("Z_g", "<f8"),
                ("delta_time", "<M8[ns]"),
                ("oc_sig_conf", "<i4"),
                ("land_sig_conf", "<i4"),
            ],
            metadata=metadata,
        )

        # then we assign each 1darray to the structured array
        photon_data = np.empty(len(X), dtype=dtype)
        photon_data["X"] = X
        photon_data["Y"] = Y
        photon_data["Z"] = Z
        photon_data["Z_g"] = Z_corrected
        photon_data["delta_time"] = delta_time
        photon_data["oc_sig_conf"] = ocean_sig
        photon_data["land_sig_conf"] = land_sig

        return photon_data
