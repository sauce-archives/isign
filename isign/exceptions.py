""" Some common exceptions """

class NotSignable(Exception):
    """ superclass for any reason why app shouldn't be
        signable """
    pass

class NotMatched(NotSignable):
    """ thrown if we can't find any app class for
        this file path """
    pass
