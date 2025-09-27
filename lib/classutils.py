##############################################################################
#
#   File Name    - Verifier.pm
#
#   Description  - A module for checking the domain specific syntax of data
#                  with regards to the structure of that data and the basic
#                  data types.
#
#                  See the POD section for further details.
#
##############################################################################
#
##############################################################################
#
#   Package      - Config::Verifier
#
#   Description  - See the POD section for further details.
#
##############################################################################






# ***** PACKAGE DETAILS *****

__all__ = ()
__version__ = '0.1'
__author__ = 'Anthony Cooper'

# ***** REQUIRED PACKAGES *****

# Standard Python packages.

import re
from copy import deepcopy
from typing import Any

class classinstancemethod(classmethod):
    def __get__(self, instance, type_):
        descr_get = super().__get__ if instance is None \
                                    else self.__func__.__get__
        return descr_get(instance, type_)
