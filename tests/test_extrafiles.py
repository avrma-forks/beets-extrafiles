# -*- coding: utf-8 -*-
"""Tests for the beets-extrafiles plugin."""
import os
import shutil
import tempfile
import unittest.mock

import beets.util.confit

import beetsplug.extrafiles

RSRC = os.path.join(os.path.dirname(__file__), 'rsrc')


class BaseTestCase(unittest.TestCase):
    """Base testcase class that sets up example files."""

    PLUGIN_CONFIG = {
        'extrafiles': {
            'patterns': {
                'log': ['*.log'],
                'cue': ['*.cue'],
                'artwork': ['scans/', 'Scans/', 'artwork/', 'Artwork/'],
            },
            'paths': {
                'artwork': '$albumpath/artwork',
                'log': '$albumpath/audio',
            },
        },
    }

    def _create_example_files(self, directory):
        for filename in ('file.cue', 'file.txt', 'file.log'):
            open(os.path.join(directory, filename), mode='w').close()

        artwork_path = os.path.join(directory, 'scans')
        os.mkdir(artwork_path)
        for filename in ('front.jpg', 'back.jpg'):
            open(os.path.join(artwork_path, filename), mode='w').close()

    def setUp(self):
        """Set up example files and instanciate the plugin."""
        self.srcdir = tempfile.TemporaryDirectory(suffix='src')
        self.dstdir = tempfile.TemporaryDirectory(suffix='dst')

        # Create example files for single directory album
        os.makedirs(os.path.join(self.srcdir.name, 'single'))
        os.makedirs(os.path.join(self.dstdir.name, 'single'))
        shutil.copy(
            os.path.join(RSRC, 'full.mp3'),
            os.path.join(self.srcdir.name, 'single', 'file.mp3'),
        )
        self._create_example_files(os.path.join(self.srcdir.name, 'single'))

        # Set up plugin instance
        config = beets.util.confit.RootView(sources=[
            beets.util.confit.ConfigSource.of(self.PLUGIN_CONFIG),
        ])

        with unittest.mock.patch(
                'beetsplug.extrafiles.beets.plugins.beets.config', config,
        ):
            self.plugin = beetsplug.extrafiles.ExtraFilesPlugin('extrafiles')

    def tearDown(self):
        """Remove the example files."""
        self.srcdir.cleanup()
        self.dstdir.cleanup()


class MatchPatternsTestCase(BaseTestCase):
    """Testcase that checks if all extra files are matched."""

    def testMatchPattern(self):
        """Test if extra files are matched in the media file's directory."""
        sourcedir = os.path.join(self.srcdir.name, 'single')
        files = set(
            (beets.util.displayable_path(path), category)
            for path, category in self.plugin.match_patterns(source=sourcedir)
        )

        expected_files = set([
            (os.path.join(sourcedir, 'scans/'), 'artwork'),
            (os.path.join(sourcedir, 'file.cue'), 'cue'),
            (os.path.join(sourcedir, 'file.log'), 'log'),
        ])

        assert files == expected_files


class MoveFilesTestCase(BaseTestCase):
    """Testcase that moves files."""

    def testMoveFilesSingle(self):
        """Test if extra files are moved for single directory imports."""
        sourcedir = os.path.join(self.srcdir.name, 'single')
        destdir = os.path.join(self.dstdir.name, 'single')

        # Move file
        source = os.path.join(sourcedir, 'file.mp3')
        destination = os.path.join(destdir, 'moved_file.mp3')
        item = beets.library.Item.from_path(source)
        shutil.move(source, destination)
        self.plugin.on_item_moved(
            item, beets.util.bytestring_path(source),
            beets.util.bytestring_path(destination),
        )

        self.plugin.on_cli_exit(None)

        # Check source directory
        assert os.path.exists(os.path.join(sourcedir, 'file.txt'))
        assert not os.path.exists(os.path.join(sourcedir, 'file.cue'))
        assert not os.path.exists(os.path.join(sourcedir, 'file.log'))
        assert not os.path.exists(os.path.join(sourcedir, 'audio.log'))

        assert not os.path.exists(os.path.join(sourcedir, 'artwork'))
        assert not os.path.exists(os.path.join(sourcedir, 'scans'))

        # Check destination directory
        assert not os.path.exists(os.path.join(destdir, 'file.txt'))
        assert os.path.exists(os.path.join(destdir, 'file.cue'))
        assert not os.path.exists(os.path.join(destdir, 'file.log'))
        assert os.path.exists(os.path.join(destdir, 'audio.log'))

        assert not os.path.isdir(os.path.join(destdir, 'scans'))
        assert os.path.isdir(os.path.join(destdir, 'artwork'))
        assert (set(os.listdir(os.path.join(destdir, 'artwork'))) ==
                set(('front.jpg', 'back.jpg')))


class CopyFilesTestCase(BaseTestCase):
    """Testcase that copies files."""

    def testCopyFilesSingle(self):
        """Test if extra files are copied for single directory imports."""
        sourcedir = os.path.join(self.srcdir.name, 'single')
        destdir = os.path.join(self.dstdir.name, 'single')

        # Copy file
        source = os.path.join(sourcedir, 'file.mp3')
        destination = os.path.join(destdir, 'copied_file.mp3')
        item = beets.library.Item.from_path(source)
        shutil.copy(source, destination)
        self.plugin.on_item_copied(
            item, beets.util.bytestring_path(source),
            beets.util.bytestring_path(destination),
        )

        self.plugin.on_cli_exit(None)

        # Check source directory
        assert os.path.exists(os.path.join(sourcedir, 'file.txt'))
        assert os.path.exists(os.path.join(sourcedir, 'file.cue'))
        assert os.path.exists(os.path.join(sourcedir, 'file.log'))
        assert not os.path.exists(os.path.join(sourcedir, 'audio.log'))

        assert not os.path.exists(os.path.join(sourcedir, 'artwork'))
        assert os.path.isdir(os.path.join(sourcedir, 'scans'))
        assert (set(os.listdir(os.path.join(sourcedir, 'scans'))) ==
                set(('front.jpg', 'back.jpg')))

        # Check destination directory
        assert not os.path.exists(os.path.join(destdir, 'file.txt'))
        assert os.path.exists(os.path.join(destdir, 'file.cue'))
        assert not os.path.exists(os.path.join(destdir, 'file.log'))
        assert os.path.exists(os.path.join(destdir, 'audio.log'))

        assert not os.path.exists(os.path.join(destdir, 'scans'))
        assert os.path.isdir(os.path.join(destdir, 'artwork'))
        assert (set(os.listdir(os.path.join(destdir, 'artwork'))) ==
                set(('front.jpg', 'back.jpg')))
