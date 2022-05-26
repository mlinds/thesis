"""Implements the Parrish Method
"""
import numpy as np

def refr_corrected_depth(depth, pointing_vector_az):
    theta2 = np.arcsin((n1/n2)*np.sin(theta1))

    R = S(n1/n2)

    S = D/np.cos(theta1)
    lambda_ = 0.5*np.pi - theta1
    P = np.sqrt(R**2+S**2-2*R*S*cos(theta1-theta2))
    alpha = np.arcsin(R*np.sin(phi)/P)

    beta = lambda_ - alpha

    yshift = P*np.cos(beta)
    zshift = P*np.sin(beta)
    
    eastingshift = yshift*np.sin(pointing_vector_az)
    northingshift = yshift*np.cos(pointing_vector_az)

    return depth
