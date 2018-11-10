# coding: utf-8
#
# Copyright © 2012-2015 Ejwa Software. All rights reserved.
#
# This file is part of gitinspector.
#
# gitinspector is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitinspector is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitinspector. If not, see <http://www.gnu.org/licenses/>.

import re
import subprocess
from enum import Enum

class Filters(Enum):
    """
    An enumeration class representing the different filter types
    """
    FILE_IN  = "file_in"
    FILE_OUT = "file_out"
    AUTHOR   = "author"
    EMAIL    = "email"
    REVISION = "revision"
    MESSAGE  = "message"

__filters__ = {
    Filters.FILE_IN:  [set(), set()],
    Filters.FILE_OUT: [set(), set()],
    Filters.AUTHOR:   [set(), set()],
    Filters.EMAIL:    [set(), set()],
    Filters.REVISION: [set(), set()],
    Filters.MESSAGE : [set(), None]
}

class InvalidRegExpError(ValueError):
    def __init__(self, msg):
        super(InvalidRegExpError, self).__init__(msg)
        self.msg = msg

# -- Unused function
# def get():
#     return __filters__

def __add_one_filter__(string,filter_type=Filters.FILE_IN):
    """
    Function that takes a string and records the corresponding filter
    inside __filters__.
    """
    for filter in Filters:
        if string.startswith(filter.value):
            __filters__[filter][0].add(string[len(filter.value) + 1:])
            return
    __filters__[Filters.FILE_IN][0].add(string)

def add_filters(string):
    """
    Add a set of filters, separated by commas. The syntax corresponds
    to the --exclude option on the command-line. If KEY is missing
    somehow, the filter is automatically Filters.FILE_IN".
    """
    rules = string.split(",")
    filter_names = [filter.value for filter in Filters]
    for rule in rules:
        split_rule = rule.split(":")
        if (len(split_rule) == 1):
            __add_one_filter__(rule)
        else:
            filter_name = split_rule[0]
            if not(filter_name in filter_names):
                raise ("Invalid filter : %s"%filter_name)
            else:
                __add_one_filter__(rule, Filters(filter_name))

def clear():
    for filter in Filters:
        __filters__[filter] = [set(), set()]

def get_filtered(filter_type=Filters.FILE_IN):
    return __filters__[filter_type][1]

# Returns True iff there is at least one active filter
def has_filtered():
    for filter in Filters:
        if __filters__[filter][1]:
            return True
    return False

def __find_commit_message__(sha):
    git_show_r = subprocess.Popen(filter(None, ["git", "show", "-s",
                                                "--pretty=%B", "-w", sha]), bufsize=1,
                                  stdout=subprocess.PIPE)
    commit_message = git_show_r.stdout.read()
    git_show_r.wait()
    git_show_r.stdout.close()

    commit_message = commit_message.strip().decode("unicode_escape", "ignore")
    commit_message = commit_message.encode("latin-1", "replace")
    return commit_message.decode("utf-8", "replace")

def is_filtered(string, filter_type):
    """
    The function that tests whether 'string' passes the filters
    defined in __filters__. The test on the string parameter depends
    on the filter_type. This function should not be used with the
    filters on types (cf. is_filtered_file).
    """

    if filter_type == Filters("file_in"):
        raise "Should not use that filter this way"

    string = string.strip()
    if not string:
        return False

    for regexp in __filters__[filter_type][0]:
        if filter_type == Filters.MESSAGE:
            search_for = __find_commit_message__(string)
        else:
            search_for = string

        try:
            if re.search(regexp, search_for) is not None:
                if filter_type == Filters.MESSAGE:
                    __add_one_filter__("revision:" + string) # ??
                else:
                    __filters__[filter_type][1].add(string)
                return True
        except:
            raise InvalidRegExpError(_("Invalid regular expression specified"))

    return False

def is_acceptable_file_name(string):
    """
    The function that tests whether 'string' passes the filters
    according to the configuration for file names. First, the filename
    must pass at least one positive check (in FILE_IN), and second, it
    must not belong to any negative check (in FILE_OUT)

    """
    search_for = string.strip()
    accepted = False
    for regexp in __filters__[Filters.FILE_IN][0]:
        try:
            if re.search(regexp, search_for) is not None:
                accepted = True
                break
        except:
            raise InvalidRegExpError(_("Invalid regular expression specified"))
    if not(accepted):
        return False
    for regexp in __filters__[Filters.FILE_OUT][0]:
        try:
            if re.search(regexp, search_for) is not None:
                __filters__[Filters.FILE_OUT][1].add(string)
                return False
        except:
            raise InvalidRegExpError(_("Invalid regular expression specified"))
    return True
