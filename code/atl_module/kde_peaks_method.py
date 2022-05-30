import numpy as np
from scipy.stats import gaussian_kde

# This code is hard to read/maintain,maybe should change to try a numpy rolling window eventually

# This function shouldn't be called directly, only from the AccumluateKDEs class so that both values can be stored
# TODO change this function to consider distance
def get_elev_at_max_density(point_array):

    # point_array = point_array[~np.isnan(point_array)]
    kde = gaussian_kde(point_array)
    # xvals = np.linspace(0,-40,400)
    kde_heights = kde.pdf(point_array)
    # find the Z value at the highest density
    max_density = kde_heights.max()
    z_at_kdemax = point_array[kde_heights.argmax()]
    # return if we don't have anything over the threshold
    # pd.DataFrame({'x':x,'y':kde_heights}).plot.scatter(x='x',y='y',xlim=[-35,0])
    return z_at_kdemax, max_density


# the above function is expensive to apply, so we can follow these instructions to avoid calling it twice:
# https://stackoverflow.com/questions/22218438/returning-two-values-from-pandas-rolling-apply
# class CountCalls:
#     def __init__(self):
#         self.counter = 0

#     def your_function(self, window):
#         retval = f(window)
#         self.counter = self.counter + 1


# TestCounter = CountCalls()

# pandas.Series.rolling(your_seriesOrDataframeColumn, window = your_window_size).apply(TestCounter.your_function)

# print TestCounter.counter


class AccumulateKDEs:
    # wtf is going on here?
    def __init__(self):
        self.index = 0
        self.index_val_list = []
        self.z_max_list = []
        self.kde_val_list = []
        self.returndict = {
            "matchup": self.index_val_list,
            "z_kde": self.z_max_list,
            "kde_val": self.kde_val_list,
        }

    def calc_kdeval_and_zval(self, zvals):
        z_max_kde, kde_val = get_elev_at_max_density(zvals)
        self.kde_val_list.append(kde_val)
        self.z_max_list.append(z_max_kde)
        self.index_val_list.append(self.index)
        self.index = self.index + 1
        # the series that is returned by the funcion is the key to matching the accumlutor to the original df
        return self.index - 1
