# Copyright (c) 2012-2016 by the GalSim developers team on GitHub
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
# https://github.com/GalSim-developers/GalSim
#
# GalSim is free software: redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions, and the disclaimer given in the accompanying LICENSE
#    file.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions, and the disclaimer given in the documentation
#    and/or other materials provided with the distribution.
#

"""@brief Tests of the LookupTable class.

Compares interpolated values a LookupTable that were created using a previous version of
the code (commit: e267f058351899f1f820adf4d6ab409d5b2605d5), using the
script devutils/external/make_table_testarrays.py
"""

from __future__ import print_function
import os
import numpy as np

from galsim_test_helpers import *

path, filename = os.path.split(__file__) # Get the path to this file for use below...
try:
    import galsim
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(path, "..")))
    import galsim

TESTDIR=os.path.join(path, "table_comparison_files")

DECIMAL = 14 # Make sure output agrees at 14 decimal places or better

# Some arbitrary args to use for the test:
args1 = range(7)  # Evenly spaced
vals1 = [ x**2 for x in args1 ]
testargs1 = [ 0.1, 0.8, 2.3, 3, 5.6, 5.9 ] # < 0 or > 7 is invalid

args2 = [ 0.7, 3.3, 14.1, 15.6, 29, 34.1, 42.5 ]  # Not evenly spaced
vals2 = [ np.sin(x*np.pi/180) for x in args2 ]
testargs2 = [ 1.1, 10.8, 12.3, 15.6, 25.6, 41.9 ] # < 0.7 or > 42.5 is invalid

interps = [ 'linear', 'spline', 'floor', 'ceil', 'nearest' ]


@timer
def test_table():
    """Test the spline tabulation of the k space Cubic interpolant.
    """
    for interp in interps:
        table1 = galsim.LookupTable(x=args1,f=vals1,interpolant=interp)
        testvals1 = [ table1(x) for x in testargs1 ]

        # The 4th item is in the args list, so it should be exactly the same as the
        # corresponding item in the vals list.
        np.testing.assert_almost_equal(testvals1[3], vals1[3], DECIMAL,
                err_msg="Interpolated value for exact arg entry does not match val entry")

        # Compare the results in testvals1 with the results if we reshape the input array to be
        # 2-dimensional.
        np.testing.assert_array_almost_equal(
            np.array(testvals1).reshape((2,3)), table1(np.array(testargs1).reshape((2,3))),
            DECIMAL,
            err_msg="Interpolated values do not match when input array shape changes")

        if interp != 'nearest':
            # Do a full regression test based on a version of the code thought to be working.
            ref1 = np.loadtxt(os.path.join(TESTDIR, 'table_test1_%s.txt'%interp))
            np.testing.assert_array_almost_equal(ref1, testvals1, DECIMAL,
                    err_msg="Interpolated values from LookupTable do not match saved "+
                    "data for evenly-spaced args, with interpolant %s."%interp)

            # Same thing, but now for args that are not evenly spaced.
            # (The Table class uses a different algorithm when the arguments are evenly spaced
            #  than when they are not.)
            table2 = galsim.LookupTable(x=args2,f=vals2,interpolant=interp)
            testvals2 = [ table2(x) for x in testargs2 ]

            np.testing.assert_almost_equal(testvals2[3], vals2[3], DECIMAL,
                    err_msg="Interpolated value for exact arg entry does not match val entry")
            ref2 = np.loadtxt(os.path.join(TESTDIR, 'table_test2_%s.txt'%interp))
            np.testing.assert_array_almost_equal(ref2, testvals2, DECIMAL,
                    err_msg="Interpolated values from LookupTable do not match saved "+
                    "data for non-evenly-spaced args, with interpolant %s."%interp)

        # Check that out of bounds arguments, or ones with some crazy shape, raise an exception:
        try:
            np.testing.assert_raises(RuntimeError,table1,args1[0]-0.01)
            np.testing.assert_raises(RuntimeError,table1,args1[-1]+0.01)
            np.testing.assert_raises(RuntimeError,table2,args2[0]-0.01)
            np.testing.assert_raises(RuntimeError,table2,args2[-1]+0.01)
            np.testing.assert_raises(ValueError,table1,np.zeros((3,3,3))+args1[0])
        except ImportError:
            print('The assert_raises tests require nose')

        # These shouldn't raise any exception:
        table1(args1[0]+0.01)
        table1(args1[-1]-0.01)
        table2(args2[0]+0.01)
        table2(args2[-1]-0.01)
        table1(np.zeros((3,3))+args1[0]+0.01)
        table1(np.zeros(3)+args1[0]+0.01)
        table1((args1[0]+0.01,args1[0]+0.01))
        table1([args1[0]+0.01,args1[0]+0.01])
        # Check 2d arrays (square)
        table1(np.zeros((3,3))+args1[0])
        # Check 2d arrays (non-square)
        table1(np.array(testargs1).reshape((2,3)))

        # Check picklability
        do_pickle(table1, lambda x: (x.getArgs(), x.getVals(), x.getInterp()))
        do_pickle(table2, lambda x: (x.getArgs(), x.getVals(), x.getInterp()))
        do_pickle(table1)
        do_pickle(table2)
        do_pickle(table1.table)
        do_pickle(table2.table)


@timer
def test_init():
    """Some simple tests of LookupTable initialization."""
    interp = 'linear'
    try:
        # Check for bad input: 1 column file, or specifying file and x, or just x, or bad
        # interpolant.
        np.testing.assert_raises(ValueError, galsim.LookupTable,
                                 file=os.path.join(TESTDIR, 'table_test1_%s.txt'%interp),
                                 x = interp)
        np.testing.assert_raises(ValueError, galsim.LookupTable,
                                 file=os.path.join(TESTDIR, 'table_test1_%s.txt'%interp))
        np.testing.assert_raises(ValueError, galsim.LookupTable,
                                 x=os.path.join(TESTDIR, 'table_test1_%s.txt'%interp))
        np.testing.assert_raises(ValueError, galsim.LookupTable,
                                 file='../examples/data/cosmo-fid.zmed1.00_smoothed.out',
                                 interpolant='foo')
    except ImportError:
        print('The assert_raises tests require nose')
    # Also make sure nothing bad happens when we try to read in a stored power spectrum and assume
    # we can use the default interpolant (spline).
    tab_ps = galsim.LookupTable(file='../examples/data/cosmo-fid.zmed1.00_smoothed.out')

    # Check picklability
    do_pickle(tab_ps)


@timer
def test_log():
    """Some simple tests of interpolation using logs."""
    # Set up some test vectors that are strictly positive, and others that are negative.
    x = 0.01*np.arange(1000)+0.01
    y = 1.*x
    x_neg = -1.*x
    y_neg = 1.*x_neg

    # Check that interpolation agrees for the positive ones when using log interpolation (for some
    # reasonable tolerance).
    tab_1 = galsim.LookupTable(x=x, f=y)
    tab_2 = galsim.LookupTable(x=x, f=y, x_log=True, f_log=True)
    tab_3 = galsim.LookupTable(x=x, f=y, x_log=True)
    tab_4 = galsim.LookupTable(x=x, f=y, f_log=True)
    test_x_vals = [2.641, 3.985, 8.123125]
    for test_val in test_x_vals:
        result_1 = tab_1(test_val)
        result_2 = tab_2(test_val)
        result_3 = tab_3(test_val)
        result_4 = tab_4(test_val)
        print(result_1, result_2, result_3, result_4)
        np.testing.assert_almost_equal(
            result_2, result_1, decimal=3,
            err_msg='Disagreement when interpolating in log(f) and log(x)')
        np.testing.assert_almost_equal(
            result_3, result_1, decimal=3,
            err_msg='Disagreement when interpolating in log(x)')
        np.testing.assert_almost_equal(
            result_4, result_1, decimal=3,
            err_msg='Disagreement when interpolating in log(f)')

    # Check picklability
    do_pickle(tab_1)
    do_pickle(tab_2)
    do_pickle(tab_3)
    do_pickle(tab_4)

    # Check storage of args and vals for log vs. linear, which should be the same to high precision.
    np.testing.assert_array_almost_equal(tab_1.getArgs(), tab_3.getArgs(), decimal=12,
                                         err_msg='Args differ for linear vs. log storage')
    np.testing.assert_array_almost_equal(tab_1.getVals(), tab_4.getVals(), decimal=12,
                                         err_msg='Vals differ for linear vs. log storage')
    # Check other properties
    assert not tab_1.x_log
    assert not tab_1.f_log
    assert tab_2.x_log
    assert tab_2.f_log
    assert tab_3.x_log
    assert not tab_3.f_log
    assert not tab_1.isLogX()
    assert not tab_1.isLogF()
    assert tab_2.isLogX()
    assert tab_2.isLogF()
    assert tab_3.isLogX()
    assert not tab_3.isLogF()

    # Check that an appropriate exception is thrown when trying to do interpolation using negative
    # ones.
    try:
        np.testing.assert_raises(ValueError, galsim.LookupTable, x=x_neg, f=y_neg, x_log=True)
        np.testing.assert_raises(ValueError, galsim.LookupTable, x=x_neg, f=y_neg, f_log=True)
        np.testing.assert_raises(ValueError, galsim.LookupTable, x=x_neg, f=y_neg, x_log=True,
                                 f_log=True)
    except ImportError:
        print('The assert_raises tests require nose')


@timer
def test_roundoff():
    table1 = galsim.LookupTable([1,2,3,4,5,6,7,8,9,10], [1,2,3,4,5,6,7,8,9,10])
    try:
        table1(1.0 - 1.e-7)
        table1(10.0 + 1.e-7)
    except:
        raise ValueError("c++ LookupTable roundoff guard failed.")
    try:
        np.testing.assert_raises(RuntimeError, table1, 1.0-1.e5)
        np.testing.assert_raises(RuntimeError, table1, 10.0+1.e5)
    except ImportError:
        print('The assert_raises tests require nose')


@timer
def test_table2d():
    """Check LookupTable2D functionality.
    """
    has_scipy = False
    try:
        import scipy
        from distutils.version import LooseVersion
        if LooseVersion(scipy.__version__) < LooseVersion('0.11'):
            raise ImportError
    except ImportError:
        print("SciPy tests require SciPy version 0.11 or greater")
    else:
        from scipy.interpolate import interp2d
        has_scipy = True

    def f(x_, y_):
        return np.sin(x_) * np.cos(y_) + x_

    x = np.linspace(0.1, 3.3, 25)
    y = np.linspace(0.2, 10.4, 75)
    yy, xx = np.meshgrid(y, x)  # Note the ordering of both input and output here!
    z = f(xx, yy)

    tab2d = galsim.LookupTable2D(x, y, z)
    do_pickle(tab2d)
    do_pickle(tab2d.table)

    newx = np.linspace(0.2, 3.1, 45)
    newy = np.linspace(0.3, 10.1, 85)
    newyy, newxx = np.meshgrid(newy, newx)

    # Compare different ways of evaluating Table2D
    ref = tab2d(newxx, newyy)
    np.testing.assert_array_almost_equal(ref, np.array([[tab2d(x0, y0)
                                                         for y0 in newy]
                                                        for x0 in newx]))
    if has_scipy:
        scitab2d = interp2d(x, y, np.transpose(z))
        np.testing.assert_array_almost_equal(ref, np.transpose(scitab2d(newx, newy)))

    # Test non-equally-spaced table.
    x = np.delete(x, 10)
    y = np.delete(y, 10)
    yy, xx = np.meshgrid(y, x)
    z = f(xx, yy)
    tab2d = galsim.LookupTable2D(x, y, z)
    ref = tab2d(newxx, newyy)
    np.testing.assert_array_almost_equal(ref, np.array([[tab2d(x0, y0)
                                                         for y0 in newy]
                                                        for x0 in newx]))
    if has_scipy:
        scitab2d = interp2d(x, y, np.transpose(z))
        np.testing.assert_array_almost_equal(ref, np.transpose(scitab2d(newx, newy)))

    # Try a simpler interpolation function.  We should be able to interpolate a (bi-)linear function
    # exactly with a linear interpolant.
    def f(x_, y_):
        return 2*x_ + 3*y_

    z = f(xx, yy)
    tab2d = galsim.LookupTable2D(x, y, z)

    np.testing.assert_array_almost_equal(f(newxx, newyy), tab2d(newxx, newyy))
    np.testing.assert_array_almost_equal(f(newxx, newyy), np.array([[tab2d(x0, y0)
                                                                   for y0 in newy]
                                                                  for x0 in newx]))

    # Test edge exception
    try:
        np.testing.assert_raises(ValueError, tab2d, 1e6, 1e6)
    except ImportError:
        print('The assert_raises tests require nose')

    # Test edge wrapping
    # Check that can't construct table with edge-wrapping if edges don't match
    try:
        np.testing.assert_raises(ValueError, galsim.LookupTable,
                                 (x, y, z), dict(edge_mode='wrap'))
    except ImportError:
        print('The assert_warns tests require nose')

    # Extend edges and make vals match
    x = np.append(x, x[-1] + (x[-1]-x[-2]))
    y = np.append(y, y[-1] + (y[-1]-y[-2]))
    z = np.pad(z,[(0,1), (0,1)], mode='wrap')
    tab2d = galsim.LookupTable2D(x, y, z, edge_mode='wrap')

    np.testing.assert_array_almost_equal(tab2d(newxx, newyy), tab2d(newxx+3*(x[-1]-x[0]), newyy))
    np.testing.assert_array_almost_equal(tab2d(newxx, newyy), tab2d(newxx, newyy+13*(y[-1]-y[0])))

    # Test edge_mode='constant'
    tab2d = galsim.LookupTable2D(x, y, z, edge_mode='constant', constant=42)
    assert type(tab2d(x[0]-1, y[0]-1)) == float
    assert tab2d(x[0]-1, y[0]-1) == 42.0
    # One in-bounds, one out-of-bounds
    np.testing.assert_array_almost_equal(tab2d([x[0], x[0]-1], [y[0], y[0]-1]),
                                         [tab2d(x[0], y[0]), 42.0])


    # Test floor/ceil/nearest interpolant
    x = y = np.arange(5)
    z = x + y[:, np.newaxis]
    tab2d = galsim.LookupTable2D(x, y, z, interpolant='ceil')
    assert tab2d(2.4, 3.6) == 3+4, "Ceil interpolant failed."
    tab2d = galsim.LookupTable2D(x, y, z, interpolant='floor')
    assert tab2d(2.4, 3.6) == 2+3, "Floor interpolant failed."
    tab2d = galsim.LookupTable2D(x, y, z, interpolant='nearest')
    assert tab2d(2.4, 3.6) == 2+4, "Nearest interpolant failed."

    # Test that x,y arrays need to be strictly increasing.
    try:
        x[0] = x[1]
        np.testing.assert_raises(ValueError, galsim.LookupTable2D, x, y, z)
        x[0] = x[1]+1
        np.testing.assert_raises(ValueError, galsim.LookupTable2D, x, y, z)
        x[0] = x[1]-1
        y[0] = y[1]
        np.testing.assert_raises(ValueError, galsim.LookupTable2D, x, y, z)
        y[0] = y[1]+1
        np.testing.assert_raises(ValueError, galsim.LookupTable2D, x, y, z)
    except ImportError:
        print('The assert_raises tests require nose')


@timer
def test_ne():
    """ Check that inequality works as expected."""
    # These should all compare as unequal.
    x = [1, 2, 3]
    f = [4, 5, 6]
    x2 = [1.1, 2.2, 3.3]
    f2 = [4.4, 5.5, 6.6]
    lts = [galsim.LookupTable(x, f),
           galsim.LookupTable(x, f2),
           galsim.LookupTable(x2, f),
           galsim.LookupTable(x, f, interpolant='floor'),
           galsim.LookupTable(x, f, x_log=True),
           galsim.LookupTable(x, f, f_log=True)]
    all_obj_diff(lts)


if __name__ == "__main__":
    test_table()
    test_init()
    test_log()
    test_roundoff()
    test_table2d()
    test_ne()
