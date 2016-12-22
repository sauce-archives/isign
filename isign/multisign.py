from os.path import basename, dirname, isdir, join
import isign
from archive import archive_factory
from signer import Signer
import logging
import multiprocessing

log = logging.getLogger(__name__)

MAX_PROCESSES = multiprocessing.cpu_count()


def get_resigned_path(original_path, credential_dir, prefix):
    """ Given:
            original_path=/path/to/original/app.ipa,
            credential_dir = /home/me/cred1
            prefix = '_foo_'
        returns:
            /path/to/original/_foo_cred1_app.ipa,
    """
    original_name = basename(original_path)
    original_dir = dirname(original_path)
    resigned_name = prefix + basename(credential_dir) + '_' + original_name
    return join(original_dir, resigned_name)


def resign(args):
    """ Given a tuple consisting of a path to an uncompressed archive,
        credential directory, and desired output path, resign accordingly.

        Returns a tuple of (credential_dir, path to resigned app) """
    ua, credential_dir, resigned_path = args

    try:
        log.debug('resigning with %s %s -> %s', ua.path, credential_dir, resigned_path)
        # get the credential files, create the 'signer'
        credential_paths = isign.get_credential_paths(credential_dir)
        signer = Signer(signer_cert_file=credential_paths['certificate'],
                        signer_key_file=credential_paths['key'],
                        apple_cert_file=isign.DEFAULT_APPLE_CERT_PATH)

        # sign it (in place)
        ua.bundle.resign(signer, credential_paths['provisioning_profile'])

        log.debug("outputing %s", resigned_path)
        # and archive it there
        ua.archive(resigned_path)
    finally:
        ua.remove()

    return (credential_dir, resigned_path)


def clone_ua(args):
    original_ua, target_ua_path = args
    log.debug('cloning %s to %s', original_ua.path, target_ua_path)
    ua = original_ua.clone(target_ua_path)
    log.debug('done cloning to %s', original_ua.path)
    return ua


def multisign(original_path, credential_dirs, info_props=None, prefix="_signed_"):
    """ Given a path to an IPA, and paths to credential directories,
        produce re-signed versions of the IPA with each credentials in the
        same directory as the original. e.g., when

            original_path=/path/to/original/app.ipa,
            credential_dirs = ['/home/me/cred1', '/home/me/cred2']
            prefix = '_foo_'

        It will generate resigned ipa archives like:
            /path/to/original/_foo_cred1_app.ipa,
            /path/to/original/_foo_cred2_app.ipa

        If info_props are provided, it will overwrite those properties in
        the app's Info.plist.

        Returns an array of tuples of [(credentials_dir, resigned app path)...]
    """
    p = multiprocessing.Pool(MAX_PROCESSES)

    # ua is potentially an isign.archive.UncompressedArchive
    ua = None

    archive = archive_factory(original_path)
    if archive is None:
        log.debug("%s didn't look like an app...", original_path)
        return

    try:
        ua = archive.unarchive_to_temp()
        if info_props:
            # Override info.plist props
            ua.bundle.update_info_props(info_props)

        # Since the signing process rewrites files, we must first create uncompressed archives
        # for each credentials_directory.
        # The first is simply the uncompressed archive we just made
        uas = [ua]

        # But the rest need to be copied. This might take a while, so let's do it in parallel
        # this will copy them to /path/to/uncompressedArchive_1, .._2, and so on
        # and make UncompressedArchive objects that can be used for resigning
        target_ua_paths = []
        for i in range(1, len(credential_dirs)):
            target_ua_paths.append((ua, ua.path + '_' + str(i)))
        uas += p.map(clone_ua, target_ua_paths)

        # now we should have one UncompressedArchive for every credential directory
        assert len(uas) == len(credential_dirs)

        # We will now construct arguments for all the resignings
        resign_args = []
        for i in range(0, len(credential_dirs)):
            resign_args += [(
                uas[i],
                credential_dirs[i],
                get_resigned_path(original_path, credential_dirs[i], prefix)
            )]
        log.debug('resign args: %s', resign_args)

        # In parallel, resign each uncompressed archive with supplied credentials,
        # and make archives in the desired paths.
        return p.map(resign, resign_args)

    except isign.NotSignable as e:
        msg = "Not signable: <{0}>: {1}\n".format(original_path, e)
        log.error(msg)
        raise

    finally:
        if ua is not None and isdir(ua.path):
            ua.remove()
