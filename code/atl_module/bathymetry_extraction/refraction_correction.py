"""Implements the Parrish Method
"""
import numpy as np


def correct_refr(depth, pointing_vector_az, pointing_vector_elev):
    """return the X,Y,Z corrections introduced by refraction, using parrish method

    Args:
        depth (float): the current depth
        pointing_vector_az (float): azimuth of pointing vector of the satellite in radians
        pointing_vector_elev (float): Elevation of pointing vector of the satellite in radians

    Returns:
        tuple: tuple of (Easting correcting, northing correction, Z correction)
    """
    refr_ind_air = 1.00029
    refr_ind_seawater = 1.34116
    theta1 = 0.5 * np.pi - pointing_vector_elev
    angl_refr = np.arcsin((refr_ind_air * np.sin(theta1)) / refr_ind_seawater)

    S = depth / np.cos(theta1)
    R = S * (refr_ind_air / refr_ind_seawater)

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
