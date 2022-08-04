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
        metadata["beam"] = beam
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

        ## ----- ASSIGNING SEGMENT-RATE VARIABLES----------- ##

        # some variables are given per 20m segment, so they need to be interpolated to assign the correct one to each photon.

        # to index these we need to set the first value to the first value of the
        # photon returns. This is because the photon time values start in the middle of a segment

        delta_time_geophys[0] = delta_time[0]

        # this will make diagnosing problems much easier.

        # get the geophysical variables
        geo_f2m_segment = (
            ds.groups[beam]
            .groups["geophys_corr"]
            .variables["geoid_free2mean"][:]
            .filled(np.NaN)
        )
        geoid_segment = (
            ds.groups[beam].groups["geophys_corr"].variables["geoid"][:].filled(np.NaN)
        )
        tide_ocean_segment = (
            ds.groups[beam]
            .groups["geophys_corr"]
            .variables["tide_ocean"][:]
            .filled(np.NaN)
        )
        pointing_vec_az_segment = (
            ds.groups[beam]
            .groups["geolocation"]
            .variables["ref_azimuth"][:]
            .filled(np.NaN)
        )
        pointing_vec_elev_segment = (
            ds.groups[beam]
            .groups["geolocation"]
            .variables["ref_elev"][:]
            .filled(np.NaN)
        )
        dac_correction_segment = (
            ds.groups[beam].groups["geophys_corr"].variables["dac"][:].filled(np.NaN)
        )
        ph_count_segment = (
            ds.groups[beam]
            .groups["geolocation"]
            .variables["segment_ph_cnt"][:]
            .filled(0)
        )

        # combine the corrections into one
        # this must be subtracted from Z ellipsoidal (see page 3 of data comparison manual v005)

        # to assign the correct correction value, we need to get the correction at a certain time
        # to do this we can align them using the pandas asof

        # switch into pandas to use as_of function
        # TODO use scipy.interpolate?
        # or maybe not: " Calling interp1d with NaNs present in input values results in undefined behaviour." from scipy.interpolate docs

        segment_level_df = pd.DataFrame(
            {
                "geoid_correction": geoid_segment,
                "tide_ocean": tide_ocean_segment,
                "geo_f2m": geo_f2m_segment,
                "pointing_vec_az": pointing_vec_az_segment,
                "pointing_vec_elev": pointing_vec_elev_segment,
                "dac_correction": dac_correction_segment,
                "ph_count_segment": ph_count_segment,
            },
            index=delta_time_geophys,
        ).sort_index()

        interpolated_df = segment_level_df.asof(delta_time).to_records()
        # get the value for every single photon
        geoid_tide_free = interpolated_df["geoid_correction"]
        tide_ocean = interpolated_df["tide_ocean"]
        geof2m = interpolated_df["geo_f2m"]
        p_vec_az = interpolated_df["pointing_vec_az"]
        p_vec_elev = interpolated_df["pointing_vec_elev"]
        dac_corr = interpolated_df["dac_correction"]
        ph_count_photon_interp = interpolated_df["ph_count_segment"]

        correction = geoid_tide_free + geof2m + tide_ocean
        # + dac_corr
        # print(len(correction))
        # get the corrected Z vals
        Z_corrected = Z - correction
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
                ("Z_ellip", "<f4"),
                ("Z_geoid", "<f4"),
                ("geoid_corr", "<f4"),
                ("tide_ocean_corr", "<f4"),
                ("geof2m_corr", "<f4"),
                # TODO there is still a rounding error on the times here
                ("delta_time", "<M8[us]"),
                ("oc_sig_conf", "<i1"),
                ("land_sig_conf", "<i1"),
                ("p_vec_az", "<f4"),
                ("p_vec_elev", "<f4"),
                ("dac_corr", "<f4"),
                ("ph_count", "<i1"),
            ],
            metadata=metadata,
        )
        # then we assign each 1darray to the structured array
        photon_data = np.empty(len(X), dtype=dtype)
        photon_data["X"] = X
        photon_data["Y"] = Y
        photon_data["Z_ellip"] = Z
        photon_data["geoid_corr"] = geoid_tide_free
        photon_data["tide_ocean_corr"] = tide_ocean
        photon_data["geof2m_corr"] = geof2m
        photon_data["Z_geoid"] = Z_corrected
        photon_data["delta_time"] = delta_time
        photon_data["oc_sig_conf"] = ocean_sig
        photon_data["land_sig_conf"] = land_sig
        photon_data["p_vec_az"] = p_vec_az
        photon_data["p_vec_elev"] = p_vec_elev
        photon_data["dac_corr"] = dac_corr
        photon_data["ph_count"] = ph_count_photon_interp

        return photon_data
