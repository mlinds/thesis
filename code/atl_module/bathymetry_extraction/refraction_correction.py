"""Implements the Parrish Method
"""
import numpy as np

# 496km orbital altitude
ICESAT_ALTITUDE = 496 * 1000

# earth radius
EARTH_RAD = 6371 * 100


def correct_refr(depth, pointing_vector_az, pointing_vector_elev):
    """return the X,Y,Z corrections introduced by refraction, using Parrish method, including the correction for the curvature of the earth (Parrish et al. 2019, 10.3390/rs11141634)

    Args:
        depth (float): the current depth
        pointing_vector_az (float): Azimuth of pointing vector of the satellite in radians
        pointing_vector_elev (float): Elevation of pointing vector of the satellite in radians

    Returns:
        tuple: tuple of (Easting correcting, northing correction, Z correction)
    """
    REFR_IND_AIR = 1.00029
    REFR_IND_SEAWATER = 1.34116
    # default theta1
    theta1 = 0.5 * np.pi - pointing_vector_elev
    # correct for earth curvature
    earth_curve_correction = np.arctan((ICESAT_ALTITUDE * np.tan(theta1)) / EARTH_RAD)
    theta1 = theta1 + earth_curve_correction

    angl_refr = np.arcsin((REFR_IND_AIR * np.sin(theta1)) / REFR_IND_SEAWATER)

    S = depth / np.cos(theta1)
    R = S * (REFR_IND_AIR / REFR_IND_SEAWATER)

    lambda_ = 0.5 * np.pi - theta1
    P = np.sqrt((R**2 + S**2) - 2 * R * S * np.cos(theta1 - angl_refr))
    phi = theta1 - angl_refr
    alpha = np.arcsin(R * np.sin(phi) / P)

    beta = lambda_ - alpha

    yshift = P * np.cos(beta)
    zshift = P * np.sin(beta)

    eastingshift = yshift * np.sin(pointing_vector_az)
    northingshift = yshift * np.cos(pointing_vector_az)

    return eastingshift, northingshift, zshift
