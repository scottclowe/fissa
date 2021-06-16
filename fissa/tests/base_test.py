'''
Provides a general testing class which inherits from unittest.TestCase
and also provides the numpy testing functions.
'''

import contextlib
import datetime
import os.path
import random
import shutil
import string
import sys
import tempfile
import unittest
from inspect import getsourcefile

import numpy as np
from numpy.testing import (assert_almost_equal,
                           assert_array_equal,
                           assert_allclose,
                           assert_equal)
import pytest


# Check where the test directory is located, to be used when fetching
# test resource files
TEST_DIRECTORY = os.path.dirname(os.path.abspath(getsourcefile(lambda: 0)))


def assert_equal_list_of_array_perm_inv(desired, actual):
    assert_equal(len(desired), len(actual))
    for desired_i in desired:
        n_matches = 0
        for actual_j in actual:
            if np.equal(actual_j, desired_i).all():
                n_matches += 1
        assert n_matches >= 0

def assert_equal_dict_of_array(desired, actual):
    assert_equal(desired.keys(), actual.keys())
    for k in desired.keys():
        assert_equal(desired[k], actual[k])

def assert_starts_with(desired, actual):
    """
    Check that a string starts with a certain substring.

    Parameters
    ----------
    desired : str
        Desired initial string.
    actual : str-like
        Actual string or string-like object.
    """
    try:
        assert len(actual) >= len(desired)
    except BaseException as err:
        print("Actual string too short ({} < {} characters)".format(len(actual), len(desired)))
        print("ACTUAL: {}".format(actual))
        raise
    try:
        return assert_equal(str(actual)[:len(desired)], desired)
    except BaseException as err:
        msg = "ACTUAL: {}".format(actual)
        if isinstance(getattr(err, "args", None), str):
            err.args += "\n" + msg
        elif isinstance(getattr(err, "args", None), tuple):
            if len(err.args) == 1:
                err.args = (err.args[0] + "\n" + msg, )
            else:
                err.args += (msg, )
        else:
            print(msg)
        raise


class BaseTestCase(unittest.TestCase):

    '''
    Superclass for all the FISSA test cases
    '''

    # Have the test directory as an attribute to the class as well as
    # a top-level variable
    test_directory = TEST_DIRECTORY

    def __init__(self, *args, **kwargs):
        '''Add test for numpy type'''
        # super(self).__init__(*args, **kw)  # Only works on Python3
        super(BaseTestCase, self).__init__(*args, **kwargs)  # Works on Python2
        self.addTypeEqualityFunc(np.ndarray, self.assert_allclose)
        self.tempdir = os.path.join(
            tempfile.gettempdir(),
            "out-" + self.generate_temp_name(),
        )

    def generate_temp_name(self, n_character=12):
        """
        Generate a random string to use as a temporary output path.
        """
        population = string.ascii_uppercase + string.digits
        if hasattr(random, "choices"):
            # Python 3.6+
            rstr = "".join(random.choices(population, k=n_character))
        else:
            # Python 2.7/3.5
            rstr = "".join(random.choice(population) for _ in range(n_character))
        return "{}-{}".format(datetime.datetime.now().strftime("%M%S%f"), rstr)

    def tearDown(self):
        # If it was created, delete the randomly generated temporary directory
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

    @contextlib.contextmanager
    def subTest(self, *args, **kwargs):
        # For backwards compatability with Python < 3.4
        if hasattr(super(BaseTestCase, self), 'subTest'):
            yield super(BaseTestCase, self).subTest(*args, **kwargs)
        else:
            yield None

    @pytest.fixture(autouse=True)
    def capsys(self, capsys):
        self.capsys = capsys

    def recapsys(self, *captures):
        """
        Capture stdout and stderr, then write them back to stdout and stderr.

        Capture is done using the `pytest.capsys` fixture.

        Parameters
        ----------
        *captures : pytest.CaptureResult, optional
            A series of extra captures to output. For each `capture` in
            `captures`, `capture.out` and `capture.err` are written to stdout
            and stderr.

        Returns
        -------
        capture : pytest.CaptureResult
            `capture.out` and `capture.err` contain all the outputs to stdout
            and stderr since the previous capture with `~pytest.capsys`.
        """
        capture_now = self.capsys.readouterr()
        for capture in captures:
            sys.stdout.write(capture.out)
            sys.stderr.write(capture.err)
        sys.stdout.write(capture_now.out)
        sys.stderr.write(capture_now.err)
        return capture_now

    def assert_almost_equal(self, *args, **kwargs):
        return assert_almost_equal(*args, **kwargs)

    def assert_array_equal(self, *args, **kwargs):
        return assert_array_equal(*args, **kwargs)

    def assert_allclose(self, *args, **kwargs):
        # Handle msg argument, which is passed from assertEqual, established
        # with addTypeEqualityFunc in __init__
        msg = kwargs.pop('msg', None)
        return assert_allclose(*args, **kwargs)

    def assert_equal(self, *args, **kwargs):
        return assert_equal(*args, **kwargs)

    def assert_equal_list_of_array_perm_inv(self, desired, actual):
        return assert_equal_list_of_array_perm_inv(desired, actual)

    def assert_equal_dict_of_array(self, desired, actual):
        return assert_equal_dict_of_array(desired, actual)

    def assert_starts_with(self, desired, actual):
        return assert_starts_with(desired, actual)
