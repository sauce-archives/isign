""" Some common exceptions """


class NotSignable(Exception):
    """ superclass for any reason why app shouldn't be
        signable """
    pass


class NotMatched(Exception):
    """ thrown if we can't find any app class for
        this file path """
    pass


class MissingHelpers(NotSignable):
    """ thrown if helper apps are missing """
    pass


class MissingCredentials(Exception):
    """ thrown if credentials are missing """
    pass


class ImproperCredentials(Exception):
    """ thrown if something looks fishy about credentials """
    pass


class OpenSslFailure(Exception):
    """ something is wrong with openssl output """
    pass
