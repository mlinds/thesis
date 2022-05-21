import numpy as np
from scipy.stats import gaussian_kde


def get_elev_at_max_density(point_array, threshold):
    # point_array = point_array[~np.isnan(point_array)]
    kde = gaussian_kde(point_array)
    kde_heights = kde.pdf(point_array)
    # find the Z value at the highest density
    z_at_kdemax = point_array[kde_heights.argmax()]
    # return if we don't have anything over the threshold
    # pd.DataFrame({'x':x,'y':kde_heights}).plot.scatter(x='x',y='y',xlim=[-35,0])
    if max(kde_heights) <= threshold:
        return np.NaN
    return z_at_kdemax
