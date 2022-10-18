
from cmath import nan
import logging
import pytest
import numpy as np
from fave import extractFormants

def test_mean_stdv():
    for test_case in provide_valuelist():
        mean, stdv = extractFormants.mean_stdv(test_case[0])
        
        assert mean == test_case[1]
        assert stdv == test_case[2]

def provide_valuelist():
    return [  
        [
            [1, 2, 3, 4],
            np.mean([1, 2, 3, 4]),
            np.std([1, 2, 3, 4], ddof=1)
        ],
        [
            [3.5, 2.6, 11.6, 34.66, 2.8, 4.7],
            np.mean([3.5, 2.6, 11.6, 34.66, 2.8, 4.7]),
            np.std([3.5, 2.6, 11.6, 34.66, 2.8, 4.7], ddof=1)
        ],
        [
            [],
            None,
            None
        ],
        [
            [23, 34, 45, 56, 12, 312, 45, 943, 21, 1, 4, 6, 9, 2],
            np.mean([23, 34, 45, 56, 12, 312, 45, 943, 21, 1, 4, 6, 9, 2]),
            np.std([23, 34, 45, 56, 12, 312, 45, 943, 21, 1, 4, 6, 9, 2], ddof=1)
        ],
        [
            [3],
            np.mean([3]),
            0
        ],
        [
            [-1],
            np.mean([-1]),
            0
        ],
        [
            [3.5, 2.6, 11.6, None, 34.66, 2.8, 4.7],
            np.nanmean(np.array([3.5, 2.6, 11.6, None, 34.66, 2.8, 4.7], 
                                dtype=np.float64)),
            np.nanstd(np.array([3.5, 2.6, 11.6, None, 34.66, 2.8, 4.7], 
                               dtype=np.float64),
                      ddof=1)
        ]
    ]

    

