"""
Tests for extraction module.
"""

from __future__ import division

import functools
import os
import shutil
import sys
import tempfile

import numpy as np
import pytest
import tifffile
from PIL import Image

from .. import extraction, roitools
from . import base_test
from .base_test import BaseTestCase

RESOURCES_DIR = os.path.join(base_test.TEST_DIRECTORY, "resources", "tiffs")


def get_dtyped_expected(expected, dtype):
    """
    Convert an input array into the format generated by ``generate_tiffs``.

    Parameters
    ----------
    expected : numpy.ndarray
        Base array, which will be modified to the format for the test.
    dtype : str
        String specifying a dtype, e.g. ``"uint8"``.

    Returns
    -------
    numpy.ndarray
        Re-formatted array.
    """
    expected = np.copy(expected)
    if "uint" in str(dtype):
        expected = np.abs(expected)
    if "float" in str(dtype):
        expected = expected / 10
    return expected.astype(dtype)


@pytest.mark.parametrize(
    "dtype",
    ["uint8", "uint16", "uint64", "int16", "int64", "float16", "float32", "float64"],
)
@pytest.mark.parametrize("datahandler", [extraction.DataHandlerTifffile])
def test_single_frame_3d(dtype, datahandler):
    """
    Test loading a regular, single-frame TIFF using `~extraction.DataHandlerTifffile`.

    The return value be 3d ``(1, 3, 2)``, including an axis for time.
    """
    expected = np.array([[[-11, 12], [14, 15], [17, 18]]])
    expected = get_dtyped_expected(expected, dtype)
    fname = os.path.join(RESOURCES_DIR, "imageio.imwrite_{}.tif".format(dtype))
    actual = datahandler.image2array(fname)
    base_test.assert_equal(actual, expected)


@pytest.mark.parametrize(
    "dtype",
    [
        "uint8",
        "uint16",
        pytest.param("uint64", marks=pytest.mark.xfail(reason="not supported")),
        "int16",
        pytest.param("int64", marks=pytest.mark.xfail(reason="not supported")),
        pytest.param("float16", marks=pytest.mark.xfail(reason="not supported")),
        "float32",
        pytest.param("float64", marks=pytest.mark.xfail(reason="not supported")),
    ],
)
@pytest.mark.parametrize("datahandler", [extraction.DataHandlerPillow])
def test_single_frame_2d(dtype, datahandler):
    """
    Test loading a regular, single-frame TIFF using `~extraction.DataHandlerPillow`.

    When we cast the output of ``datahandler.image2array(fname)`` as a
    :class:`numpy.ndarray`, the return value will be 2d, shaped ``(3, 2)``
    without an axis for time. This is fine because the other methods in
    `~extraction.DataHandlerPillow` do not interact with the :class:`PIL.Image`
    object in this way.
    """
    expected = np.array([[-11, 12], [14, 15], [17, 18]])
    expected = get_dtyped_expected(expected, dtype)
    fname = os.path.join(RESOURCES_DIR, "imageio.imwrite_{}.tif".format(dtype))
    actual = datahandler.image2array(fname)
    base_test.assert_equal(actual, expected)


def check_multiframe_image2array(base_fname, dtype, datahandler):
    """
    Check a multiframe TIFF file loads correctly.

    Helper function called by tests.

    Parameters
    ----------
    base_fname : str
        Base file name, for example ``"tifffile.imsave.bigtiff"``.
    dtype : str
        String representation of a data type, e.g. ``"uint8"``.
    datahandler : extraction.DataHandlerAbstract
        An object bearing an ``image2array`` method under test. The return
        value of ``np.asarray(datahandler.image2array)`` should be the entire
        contents of the TIFF file.
    """
    expected = np.array(
        [
            [[-11, 12], [14, 15], [17, 18]],
            [[21, 22], [24, 25], [27, 28]],
            [[31, 32], [34, 35], [37, 38]],
            [[41, 42], [44, 45], [47, 48]],
            [[51, 52], [54, 55], [57, 58]],
            [[61, 62], [64, 55], [67, 68]],
        ]
    )
    expected = get_dtyped_expected(expected, dtype)
    fname = os.path.join(RESOURCES_DIR, base_fname + "_{}.tif".format(dtype))
    actual = datahandler.image2array(fname)
    base_test.assert_equal(actual, expected)


@pytest.mark.parametrize(
    "base_fname",
    [
        "tifffile.imsave",
        "tifffile.imsave.bigtiff",
        "TiffWriter.mixedA",
        "TiffWriter.mixedB",
        "TiffWriter.mixedC",
        "TiffWriter.save",
        "TiffWriter.write.contiguous",
        "TiffWriter.write.discontiguous",
    ],
)
@pytest.mark.parametrize(
    "dtype",
    ["uint8", "uint16", "uint64", "int16", "int64", "float16", "float32", "float64"],
)
@pytest.mark.parametrize("datahandler", [extraction.DataHandlerTifffile])
def test_multiframe_image2array(base_fname, dtype, datahandler):
    """
    Test loading TIFFs with :class:`~extraction.DataHandlerTifffile`.
    """
    fn = functools.partial(
        check_multiframe_image2array,
        base_fname=base_fname,
        dtype=dtype,
        datahandler=datahandler,
    )
    if ".mixedB" in base_fname and sys.version_info >= (3, 2):
        with BaseTestCase().assertWarnsRegex(
            UserWarning, ".*dimensions .*will be .*flattened.*"
        ):
            return fn()
    else:
        return fn()


@pytest.mark.parametrize("dtype", ["uint8", "uint16", "float32"])
@pytest.mark.parametrize("datahandler", [extraction.DataHandlerTifffile])
def test_multiframe_image2array_imagejformat(dtype, datahandler):
    """
    Test loading ImageJ format TIFFs with :class:`~extraction.DataHandlerTifffile`.
    """
    return check_multiframe_image2array(
        base_fname="tifffile.imsave.imagej",
        dtype=dtype,
        datahandler=datahandler,
    )


@pytest.mark.parametrize(
    "base_fname",
    [
        "tifffile.imsave",
        "tifffile.imsave.bigtiff",
        "TiffWriter.save",
        "TiffWriter.write.contiguous",
        "TiffWriter.write.discontiguous",
    ],
)
@pytest.mark.parametrize("dtype", ["uint8"])
@pytest.mark.parametrize("shp", ["3,2,3,2", "2,1,3,3,2", "2,3,1,1,3,2"])
@pytest.mark.parametrize("datahandler", [extraction.DataHandlerTifffile])
def test_multiframe_image2array_higherdim(base_fname, shp, dtype, datahandler):
    """
    Test loading 4d and 5d TIFFs with :class:`~extraction.DataHandlerTifffile`.
    """
    fn = functools.partial(
        check_multiframe_image2array,
        base_fname=base_fname + "_" + shp,
        dtype=dtype,
        datahandler=datahandler,
    )
    if shp == "2,1,3,3,2" and sys.version_info >= (3, 2):
        with BaseTestCase().assertWarnsRegex(
            UserWarning, ".*dimensions .*will be .*flattened.*"
        ):
            return fn()
    else:
        return fn()


def check_multiframe_mean(base_fname, dtype, datahandler):
    """
    Check the mean of a loaded multiframe TIFF is correct.

    Helper function called by tests.

    Parameters
    ----------
    base_fname : str
        Base file name, for example ``"tifffile.imsave.bigtiff"``.
    dtype : str
        String representation of a data type, e.g. ``"uint8"``.
    datahandler : extraction.DataHandlerAbstract
        An object bearing an ``image2array`` method and ``getmean`` method,
        both of which will be tested. The return value of
        ``np.asarray(datahandler.getmean(datahandler.image2array(fname)))``
        must match the average over the contents of the TIFF file.
    """
    expected = np.array(
        [
            [[-11, 12], [14, 15], [17, 18]],
            [[21, 22], [24, 25], [27, 28]],
            [[31, 32], [34, 35], [37, 38]],
            [[41, 42], [44, 45], [47, 48]],
            [[51, 52], [54, 55], [57, 58]],
            [[61, 62], [64, 55], [67, 68]],
        ]
    )
    expected = get_dtyped_expected(expected, dtype)
    expected = np.mean(expected, dtype=np.float64, axis=0)
    fname = os.path.join(RESOURCES_DIR, base_fname + "_{}.tif".format(dtype))
    data = datahandler.image2array(fname)
    actual = datahandler.getmean(data)
    base_test.assert_allclose(actual, expected)


@pytest.mark.parametrize(
    "base_fname",
    [
        "tifffile.imsave",
        "tifffile.imsave.bigtiff",
        "TiffWriter.mixedA",
        "TiffWriter.mixedB",
        "TiffWriter.mixedC",
        "TiffWriter.save",
        "TiffWriter.write.contiguous",
        "TiffWriter.write.discontiguous",
    ],
)
@pytest.mark.parametrize(
    "dtype",
    [
        "uint8",
        "uint16",
        "uint64",
        "int16",
        "int64",
        "float16",
        "float32",
        "float64",
    ],
)
@pytest.mark.parametrize(
    "datahandler", [extraction.DataHandlerTifffile, extraction.DataHandlerTifffileLazy]
)
def test_multiframe_mean(base_fname, dtype, datahandler):
    """
    Test the mean of TIFFs.
    """
    fn = functools.partial(
        check_multiframe_mean,
        base_fname=base_fname,
        dtype=dtype,
        datahandler=datahandler,
    )
    if ".mixedB" in base_fname and sys.version_info >= (3, 2):
        with BaseTestCase().assertWarnsRegex(
            UserWarning, ".*dimensions .*will be .*flattened.*"
        ):
            return fn()
    else:
        return fn()


@pytest.mark.parametrize(
    "base_fname",
    [
        "tifffile.imsave",
        pytest.param(
            "tifffile.imsave.bigtiff", marks=pytest.mark.xfail(reason="not supported")
        ),
        "TiffWriter.mixedA",
        # "TiffWriter.mixedB" is not supported
        "TiffWriter.mixedC",
        "TiffWriter.save",
        "TiffWriter.write.contiguous",
        "TiffWriter.write.discontiguous",
    ],
)
@pytest.mark.parametrize(
    "dtype",
    [
        "uint8",
        "uint16",
        # pytest.param("uint64", marks=pytest.mark.xfail(reason="not supported")),
        "int16",
        # pytest.param("int64", marks=pytest.mark.xfail(reason="not supported")),
        # pytest.param("float16", marks=pytest.mark.xfail(reason="not supported")),
        "float32",
        # pytest.param("float64", marks=pytest.mark.xfail(reason="not supported")),
    ],
)
@pytest.mark.parametrize("datahandler", [extraction.DataHandlerPillow])
def test_multiframe_mean_pillow(base_fname, dtype, datahandler):
    """
    Test the mean of TIFFs loaded with :class:`~extraction.DataHandlerPillow`.
    """
    return check_multiframe_mean(
        base_fname=base_fname, dtype=dtype, datahandler=datahandler
    )


@pytest.mark.parametrize("dtype", ["uint8", "uint16", "float32"])
@pytest.mark.parametrize(
    "datahandler",
    [
        extraction.DataHandlerTifffile,
        extraction.DataHandlerTifffileLazy,
        extraction.DataHandlerPillow,
    ],
)
def test_multiframe_mean_imagejformat(dtype, datahandler):
    """
    Test the mean of ImageJ format TIFF files.

    This is broken up from the other formats because fewer dtypes are supported
    by imagej format TIFF files, and so they can't be parametrized together.
    """
    return check_multiframe_mean(
        base_fname="tifffile.imsave.imagej",
        dtype=dtype,
        datahandler=datahandler,
    )


@pytest.mark.parametrize(
    "base_fname",
    [
        "tifffile.imsave",
        "tifffile.imsave.bigtiff",
        "TiffWriter.save",
        "TiffWriter.write.contiguous",
        "TiffWriter.write.discontiguous",
    ],
)
@pytest.mark.parametrize("dtype", ["uint8"])
@pytest.mark.parametrize("shp", ["3,2,3,2", "2,1,3,3,2", "2,3,1,1,3,2"])
@pytest.mark.parametrize(
    "datahandler", [extraction.DataHandlerTifffile, extraction.DataHandlerTifffileLazy]
)
def test_multiframe_mean_higherdim(base_fname, shp, dtype, datahandler):
    """
    Test the mean of 4d/5d TIFFs.
    """
    fn = functools.partial(
        check_multiframe_mean,
        base_fname=base_fname + "_" + shp,
        dtype=dtype,
        datahandler=datahandler,
    )
    if shp == "2,1,3,3,2" and sys.version_info >= (3, 2):
        with BaseTestCase().assertWarnsRegex(
            UserWarning, ".*dimensions .*will be .*flattened.*"
        ):
            return fn()
    else:
        return fn()


@pytest.mark.parametrize(
    "base_fname",
    [
        "tifffile.imsave",
        # "tifffile.imsave.bigtiff" is not supported
        "TiffWriter.save",
        "TiffWriter.write.contiguous",
        "TiffWriter.write.discontiguous",
    ],
)
@pytest.mark.parametrize("dtype", ["uint8"])
@pytest.mark.parametrize(
    "shp",
    [
        "3,2,3,2",
        pytest.param("2,1,3,3,2", marks=pytest.mark.xfail(reason="looks like RGB")),
        "2,3,1,1,3,2",
    ],
)
@pytest.mark.parametrize("datahandler", [extraction.DataHandlerPillow])
def test_multiframe_mean_higherdim_pillow(base_fname, shp, dtype, datahandler):
    """
    Test the mean of 4d/5d TIFFs loaded with :class:`~extraction.DataHandlerPillow`.
    """
    return check_multiframe_mean(
        base_fname=base_fname + "_" + shp,
        dtype=dtype,
        datahandler=datahandler,
    )


class TestDataHandlerRepr(BaseTestCase):
    """String representations of DataHandler are correct."""

    def test_repr_tifffile(self):
        datahandler = extraction.DataHandlerTifffile()
        self.assert_equal(repr(datahandler), "fissa.extraction.DataHandlerTifffile()")

    def test_repr_tifffile_lazy(self):
        datahandler = extraction.DataHandlerTifffileLazy()
        self.assert_equal(
            repr(datahandler), "fissa.extraction.DataHandlerTifffileLazy()"
        )

    def test_repr_pillow(self):
        datahandler = extraction.DataHandlerPillow()
        self.assert_equal(repr(datahandler), "fissa.extraction.DataHandlerPillow()")


class Rois2MasksTestMixin:
    """Tests for rois2masks."""

    polys = [
        np.array([[39.0, 62.0], [60.0, 45.0], [48.0, 71.0]]),
        np.array([[72.0, 107.0], [78.0, 130.0], [100.0, 110.0]]),
    ]

    def setUp(self):
        self.expected = roitools.getmasks(self.polys, (176, 156))
        self.data = np.zeros((1, 176, 156))
        # Child class must declare self.datahandler

    def test_imagej_zip(self):
        # load zip of rois
        ROI_loc = os.path.join(self.test_directory, "resources", "RoiSet.zip")
        actual = self.datahandler.rois2masks(ROI_loc, self.data)

        # assert equality
        self.assert_equal(actual, self.expected)

    def test_arrays(self):
        # load from array
        actual = self.datahandler.rois2masks(self.polys, self.data)
        # assert equality
        self.assert_equal(actual, self.expected)

    def test_transposed_polys(self):
        # load from array
        actual = self.datahandler.rois2masks([x.T for x in self.polys], self.data)
        # assert equality
        self.assert_equal(actual, self.expected)

    def test_masks(self):
        # load from masks
        actual = self.datahandler.rois2masks(self.expected, self.data)

        # assert equality
        self.assert_equal(actual, self.expected)

    def test_rois_not_list(self):
        # check that rois2masks fails when the rois are not a list
        with self.assertRaises(TypeError):
            self.datahandler.rois2masks({}, self.data)
        with self.assertRaises(TypeError):
            self.datahandler.rois2masks(self.polys[0], self.data)

    def test_polys_1d(self):
        # check that rois2masks fails when the polys are not 2d
        polys1d = [
            np.array([[39.0]]),
            np.array([[72.0]]),
        ]
        with self.assertRaises(ValueError):
            self.datahandler.rois2masks(polys1d, self.data)

    def test_polys_3d(self):
        # check that rois2masks fails when the polys are not 2d
        polys3d = [
            np.array([[39.0, 62.0, 0.0], [60.0, 45.0, 0.0], [48.0, 71.0, 0.0]]),
            np.array([[72.0, 107.0, 0.0], [78.0, 130.0, 0.0], [100.0, 110.0, 0.0]]),
        ]
        with self.assertRaises(ValueError):
            self.datahandler.rois2masks(polys3d, self.data)


class TestRois2MasksRoitools(BaseTestCase, Rois2MasksTestMixin):
    """Test roitools.rois2masks."""

    def setUp(self):
        Rois2MasksTestMixin.setUp(self)
        self.data = (176, 156)
        self.datahandler = roitools


class TestRois2MasksTifffile(BaseTestCase, Rois2MasksTestMixin):
    """Tests for rois2masks using `~extraction.DataHandlerTifffile`."""

    def setUp(self):
        Rois2MasksTestMixin.setUp(self)
        self.datahandler = extraction.DataHandlerTifffile()


class TestRois2MasksTifffileLazy(BaseTestCase, Rois2MasksTestMixin):
    """Tests for rois2masks using `~extraction.DataHandlerTifffileLazy`."""

    def setUp(self):
        Rois2MasksTestMixin.setUp(self)
        os.makedirs(self.tempdir)
        self.filename = os.path.join(self.tempdir, "tmp.tif")
        tifffile.imsave(self.filename, self.data)
        self.data = tifffile.TiffFile(self.filename)
        self.datahandler = extraction.DataHandlerTifffileLazy()

    def tearDown(self):
        self.data.close()
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)


class TestRois2MasksPillow(BaseTestCase, Rois2MasksTestMixin):
    """Tests for rois2masks using `~extraction.DataHandlerPillow`."""

    def setUp(self):
        Rois2MasksTestMixin.setUp(self)
        self.data = Image.fromarray(
            self.data.reshape(self.data.shape[-2:]).astype(np.uint8)
        )
        self.datahandler = extraction.DataHandlerPillow()
