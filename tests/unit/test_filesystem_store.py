# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack, LLC
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Tests the filesystem backend store"""

import StringIO
import hashlib
import unittest
import urlparse

import stubout

from glance.common import exception
from glance.store.filesystem import FilesystemBackend, ChunkedFile
from tests import stubs

FILESYSTEM_OPTIONS = {
    'verbose': True,
    'debug': True,
    'filesystem_store_datadir': stubs.FAKE_FILESYSTEM_ROOTDIR}


class TestFilesystemBackend(unittest.TestCase):

    def setUp(self):
        """Establish a clean test environment"""
        self.stubs = stubout.StubOutForTesting()
        stubs.stub_out_filesystem_backend()
        self.orig_chunksize = ChunkedFile.CHUNKSIZE
        ChunkedFile.CHUNKSIZE = 10

    def tearDown(self):
        """Clear the test environment"""
        stubs.clean_out_fake_filesystem_backend()
        self.stubs.UnsetAll()
        ChunkedFile.CHUNKSIZE = self.orig_chunksize

    def test_get(self):
        """Test a "normal" retrieval of an image in chunks"""
        url_pieces = urlparse.urlparse("file:///tmp/glance-tests/2")
        image_file = FilesystemBackend.get(url_pieces)

        expected_data = "chunk00000remainder"
        expected_num_chunks = 2
        data = ""
        num_chunks = 0

        for chunk in image_file:
            num_chunks += 1
            data += chunk
        self.assertEqual(expected_data, data)
        self.assertEqual(expected_num_chunks, num_chunks)

    def test_get_non_existing(self):
        """
        Test that trying to retrieve a file that doesn't exist
        raises an error
        """
        url_pieces = urlparse.urlparse("file:///tmp/glance-tests/non-existing")
        self.assertRaises(exception.NotFound,
                          FilesystemBackend.get,
                          url_pieces)

    def test_add(self):
        """Test that we can add an image via the filesystem backend"""
        ChunkedFile.CHUNKSIZE = 1024
        expected_image_id = 42
        expected_file_size = 1024 * 5  # 5K
        expected_file_contents = "*" * expected_file_size
        expected_checksum = hashlib.md5(expected_file_contents).hexdigest()
        expected_location = "file://%s/%s" % (stubs.FAKE_FILESYSTEM_ROOTDIR,
                                              expected_image_id)
        image_file = StringIO.StringIO(expected_file_contents)

        location, size, checksum = FilesystemBackend.add(42, image_file,
                                                         FILESYSTEM_OPTIONS)

        self.assertEquals(expected_location, location)
        self.assertEquals(expected_file_size, size)
        self.assertEquals(expected_checksum, checksum)

        url_pieces = urlparse.urlparse("file:///tmp/glance-tests/42")
        new_image_file = FilesystemBackend.get(url_pieces)
        new_image_contents = ""
        new_image_file_size = 0

        for chunk in new_image_file:
            new_image_file_size += len(chunk)
            new_image_contents += chunk

        self.assertEquals(expected_file_contents, new_image_contents)
        self.assertEquals(expected_file_size, new_image_file_size)

    def test_add_already_existing(self):
        """
        Tests that adding an image with an existing identifier
        raises an appropriate exception
        """
        image_file = StringIO.StringIO("nevergonnamakeit")
        options = {'verbose': True,
                   'debug': True,
                   'filesystem_store_datadir': stubs.FAKE_FILESYSTEM_ROOTDIR}
        self.assertRaises(exception.Duplicate,
                          FilesystemBackend.add,
                          2, image_file, FILESYSTEM_OPTIONS)

    def test_delete(self):
        """
        Test we can delete an existing image in the filesystem store
        """
        url_pieces = urlparse.urlparse("file:///tmp/glance-tests/2")

        FilesystemBackend.delete(url_pieces)

        self.assertRaises(exception.NotFound,
                          FilesystemBackend.get,
                          url_pieces)

    def test_delete_non_existing(self):
        """
        Test that trying to delete a file that doesn't exist
        raises an error
        """
        url_pieces = urlparse.urlparse("file:///tmp/glance-tests/non-existing")
        self.assertRaises(exception.NotFound,
                          FilesystemBackend.delete,
                          url_pieces)