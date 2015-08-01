""""
isign creates big temporary files, using the standard tempfile library.
If they are not cleaned up, they can fill up the disk. This has
already happened in production. :(

This library monkey-patches tempfile to use our own temporary
directory, so it's easy to test that we aren't leaving any temp files behind.
"""
import os
import shutil
import tempfile


class MonitorTempFile(object):
    TEMP_DIR = None

    @classmethod
    def mkdtemp(cls, *args, **kwargs):
        """ ensure temp directories are subdirs of TEMP_DIR """
        kwargs['dir'] = MonitorTempFile.TEMP_DIR
        return tempfile._original_mkdtemp(*args, **kwargs)

    @classmethod
    def mkstemp(cls, *args, **kwargs):
        """ ensure temp files are within TEMP_DIR """
        kwargs['dir'] = MonitorTempFile.TEMP_DIR
        return tempfile._original_mkstemp(*args, **kwargs)

    @classmethod
    def NamedTemporaryFile(cls, *args, **kwargs):
        """ ensure named temp files are within TEMP_DIR """
        kwargs['dir'] = MonitorTempFile.TEMP_DIR
        return tempfile._original_NamedTemporaryFile(*args, **kwargs)

    @classmethod
    def start(cls):
        """ swap a few methods in tempfile with our versions that limit them
            to a particular directory """

        if hasattr(tempfile, '_is_patched') and tempfile._is_patched:
            raise Exception("need tempfile to be in unpatched state!")

        cls.TEMP_DIR = tempfile.mkdtemp(prefix='isign-test-run-')

        tempfile._original_mkdtemp = tempfile.mkdtemp
        tempfile.mkdtemp = MonitorTempFile.mkdtemp

        tempfile._original_mkstemp = tempfile.mkstemp
        tempfile.mkstemp = MonitorTempFile.mkstemp

        tempfile._original_NamedTemporaryFile = tempfile.NamedTemporaryFile
        tempfile.NamedTemporaryFile = MonitorTempFile.NamedTemporaryFile

        tempfile._is_patched = True

    @classmethod
    def stop(cls):
        """ restore a few methods in tempfile. opposite of _tempfile_patch """
        tempfile.mkdtemp = tempfile._original_mkdtemp
        tempfile.mkstemp = tempfile._original_mkstemp
        tempfile.NamedTemporaryFile = tempfile._original_NamedTemporaryFile

        tempfile._is_patched = False

        shutil.rmtree(cls.TEMP_DIR)

        cls.TEMP_DIR = None

    @classmethod
    def get_temp_files(cls):
        return os.listdir(cls.TEMP_DIR)

    @classmethod
    def has_no_temp_files(cls):
        """ check if this test has created any temp files which
            aren't cleaned up """
        if cls.TEMP_DIR is None:
            raise Exception("temp dir is None. Maybe call patch() first?")
        return len(cls.get_temp_files()) == 0
