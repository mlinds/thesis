import numpy as np
from sklearn.metrics import mean_squared_error


def calc_rms_error(beam_df, column_names: list):
    error_dict = {}
    # go over the each DEM, and find the RMS error with the calculated seafloor
    for column in column_names:
        # get a subset of the dataframe that is the seafloor and the column of interest
        comp_columns = beam_df.loc[:, ["sf_refr", column]].dropna()
        if len(comp_columns) == 0:
            error_dict[str(column) + "_error"] = np.NaN
        else:
            rms_error = mean_squared_error(
                comp_columns.loc[:, column], comp_columns.loc[:, "sf_refr"]
            )
            error_dict[str(column) + "_error"] = rms_error

    return error_dict
