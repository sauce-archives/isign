from os.path import isdir
import isign
from archive import archive_factory
from signer import Signer
import logging
import multiprocessing

log = logging.getLogger(__name__)

MAX_PROCESSES = multiprocessing.cpu_count()


def resign(args):
    """ Given a tuple consisting of a path to an uncompressed archive,
        credential directory, and desired output path, resign accordingly.

        Returns a tuple of (cred_dir, path to resigned app) """
    ua, cred_dir, resigned_path = args

    try:
        log.debug('resigning with %s %s -> %s', ua.path, cred_dir, resigned_path)
        # get the credential files, create the 'signer'
        credential_paths = isign.get_credential_paths(cred_dir)
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

    return (cred_dir, resigned_path)


def clone_ua(args):
    original_ua, target_ua_path = args
    log.debug('cloning %s to %s', original_ua.path, target_ua_path)
    ua = original_ua.clone(target_ua_path)
    log.debug('done cloning to %s', original_ua.path)
    return ua


def multisign(original_path, cred_dirs_to_output_paths, info_props=None):
    """ Given a path to an app,
        a mapping of credential directories to desired output paths,
        optional info.plist properties to overwrite,

        produce re-signed versions of the app as desired.

        See: multisign_archive, which this wraps.

        Returns an array of tuples of [(credentials_dir, resigned app path)...]
    """

    archive = archive_factory(original_path)
    if archive is None:
        log.debug("%s didn't look like an app...", original_path)
        return None

    return multisign_archive(archive, cred_dirs_to_output_paths, info_props)


def multisign_archive(archive, cred_dirs_to_output_paths, info_props=None):
    """ Given an isign.archive object,
        a mapping of credential directories to desired output paths,
        optional info.plist properties to overwrite,

        produce re-signed versions of the IPA.

        If info_props are provided, it will overwrite those properties in
        the app's Info.plist.

        Returns an array of tuples of [(credentials_dir, resigned app path)...]
    """

    # get ready for multiple processes...
    p = multiprocessing.Pool(MAX_PROCESSES)

    # ua is potentially an isign.archive.UncompressedArchive
    ua = None

    results = []

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
        for i in range(1, len(cred_dirs_to_output_paths)):
            target_ua_paths.append((ua, ua.path + '_' + str(i)))
        uas += p.map(clone_ua, target_ua_paths)

        # now we should have one UncompressedArchive for every credential directory
        assert len(uas) == len(cred_dirs_to_output_paths)

        # We will now construct arguments for all the resignings
        resign_args = []
        for i, (cred_dir, output_path) in enumerate(cred_dirs_to_output_paths.items()):
            resign_args.append((uas[i], cred_dir, output_path))
        log.debug('resign args: %s', resign_args)

        # In parallel, resign each uncompressed archive with supplied credentials,
        # and make archives in the desired paths.
        results = p.map(resign, resign_args)

    except isign.NotSignable as e:
        msg = "Not signable: <{0}>: {1}\n".format(archive.path, e)
        log.error(msg)
        raise

    finally:
        if ua is not None and isdir(ua.path):
            ua.remove()

    return results
