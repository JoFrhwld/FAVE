#!/usr/bin/env python
# Mahalanobis distance function for extractFormants.py
# Kyle Gorman <gormanky@ohsu.edu>

import numpy as np


def mahalanobis(u, v, ic):
    """
    Compute Mahalanobis distance between two 1d vectors _u_, _v_ with
    sample inverse covariance matrix _ic_; a ValueError will be thrown
    if dimensions are incorrect. 

    Mahalanobis distance is defined as 

    \sqrt{(u - v) \sum^{-1} (u - v)^T}

    where \sum^{-1} is the sample inverse covariance matrix. A particularly
    useful case is when _u_ is an observation, _v_ is the mean of some 
    sample, and _ic_ is the inverse covariance matrix of the same sample.


    # if _ic_ is an identity matrix, this becomes the Euclidean distance
    >>> N = 5
    >>> ic = np.eye(N)
    >>> u = np.array([1 for _ in xrange(N)])
    >>> v = np.array([0 for _ in xrange(N)])
    >>> mahalanobis(u, v, ic) == np.sqrt(N)
    True

    # check against scipy; obviously this depends on scipy

    >>> u = np.random.random(N)
    >>> v = np.random.random(N)
    >>> ic = np.linalg.inv(np.cov(np.random.random((N, N * N))))
    >>> from scipy.spatial.distance import mahalanobis as mahalanobis_scipy
    >>> mahalanobis(u, v, ic) == mahalanobis_scipy(u, v, ic)
    True
    """
    # these coercions are free if u and v are already matrices
    diff = np.asmatrix(np.asarray(u) - np.asarray(v))
    # ic will be coerced to type matrix if it is not already
    return float(np.sqrt(diff * ic * diff.T))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
