# %%
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from scipy.signal import find_peaks

# %%
def get_elev_at_max_density(point_array, threshold):
    kde = gaussian_kde(point_array)
    kde_heights = kde.pdf(point_array)

    # find the Z value at the highest density
    z_at_kdemax = point_array[kde_heights.argmax()]
    # return if we don't have anything over the threshold
    if max(kde_heights) <= threshold:
        return np.NaN
    # get the peaks of the density function
    # peaks, properties = find_peaks(
    #     kde_heights,
    #     # limit the high so if there is not sufficient signal, it will return NA
    #     height=threshold,
    #     # don't get points next to one another
    #     distance=10,
    #     # this is only added to force it to calculate promenince
    #     prominence=0.0,
    # )
    # find the Z value at the peak
    # peak_zvals = point_array[peaks]
    # get the lower (i.e. deeper) of the two most prominent peaks
    # return min(peak_zvals[properties["prominences"].argsort()][:2])
    return z_at_kdemax


# %%
