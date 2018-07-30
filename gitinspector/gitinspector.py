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

import argparse
import ast
import atexit
import datetime
import io
import os
import sys
from .blame import Blame
from .changes import Changes
from .config import GitConfig
from .metrics import MetricsLogic
from .repository import Repository
from . import (basedir, extensions, filtering, format, interval,
               localization, terminal, version)
from .output import outputable

from .extensions import DEFAULT_EXTENSIONS
from .format import __available_formats__

localization.init()

class StdoutWriter(io.StringIO):
    def __init__(self):
        io.StringIO.__init__(self)
    def writeln(self, string):
        self.write(string + "\n")
    def close(self):
        print(self.getvalue())
        io.StringIO.close(self)


class FileWriter(object):
    def __init__(self, file):
        self.file = file
    def write(self, string):
        self.file.write(string)
    def writeln(self, string):
        self.file.write(string + "\n")
    def close(self):
        self.file.close()


class Runner(object):
    def __init__(self, config, writer):
        self.config = config  # Namespace object containing the config
        self.out = writer     # Buffer for containing the output

        # Initialize a list of Repository objects
        self.repos = __get_validated_git_repos__(config.repositories)
        # We need the repos above to be set before we read the git config.
        GitConfig(self, self.repos[-1].location).read()
        # Initialize extensions and formats
        extensions.define(config.file_types)
        format.select(config.format)
        # Initialize bounds on commits dates
        if config.since:
            interval.set_since(config.since.strftime('%Y-%m-%d'))
        if config.until:
            interval.set_until(config.until.strftime('%Y-%m-%d'))

        # The following objects are additive : they begin empty, and
        # then one instance is added to the Runner for each repository
        self.changes = Changes.empty()      # Changes object
        self.blames = Blame.empty()         # Blame object
        self.metrics = MetricsLogic.empty() # Metrics object

    def __load__(self):
        """
        Load a list of repositories `repos`, compute the changes, the
        blames and possibly the metrics.
        """
        localization.check_compatibility(version.__version__)

        # if not self.config.localize_output:
        #     localization.disable()

        terminal.skip_escapes(not sys.stdout.isatty())
        terminal.set_stdout_encoding()
        previous_directory = os.getcwd()

        for repo in self.repos:
            os.chdir(repo.location)
            repo = repo if len(self.repos) > 1 else None
            repo_changes = Changes(repo, self.config)
            self.blames += Blame(repo, repo_changes, self.config)
            self.changes += repo_changes

            if self.config.metrics:
                self.metrics += MetricsLogic()

            if self.config.progress and sys.stdout.isatty() and format.is_interactive_format():
                terminal.clear_row()

        os.chdir(previous_directory)

    def __output__(self):
        """
        Output the results of the run.
        """
        if self.config.silent:
            return

        format.output_header(self)
        for out in outputable.Outputable.list():
            out(self).output()
        format.output_footer(self)

        self.out.close()

    def process(self):
        """
        Launch a full run, loading the repositories and possibly outputting the results.
        """
        self.__load__()
        self.__output__()


def __check_python_version__():
    """
    Check for a sufficiently recent python version.
    """
    if sys.version_info < (3, 6):
        python_version = str(sys.version_info[0]) + "." + str(sys.version_info[1])
        sys.exit(_("gitinspector requires at least Python 3.6"
                   "to run (version {0} was found).").format(python_version))


def __get_validated_git_repos__(repos_relative):
    """
    Convert a list of paths into a list of Repository objects.
    """
    if not repos_relative:
        repos_relative = ["."]

    repos = []

    # Try to clone the repos or return the same directory and bail out.
    for repo in repos_relative:
        cloned_repo = Repository.create(repo)

        if cloned_repo.name is None:
            cloned_repo.location = basedir.get_basedir_git(cloned_repo.location)
            cloned_repo.name = os.path.basename(cloned_repo.location)

        repos.append(cloned_repo)

    return repos


def __parse_arguments__(args=None):
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=
                                     _("List information about the repository in REPOSITORY. If no repository is \n"
                                       "specified, the current directory is used. If multiple repositories are \n"
                                       "given, information will be merged into a unified statistical report."), epilog=
                                     _("gitinspector will filter statistics to only include commits that modify, \n"
                                       "add or remove one of the specified extensions, see -f or --file-types for \n"
                                       "more information. \n\n"
                                       "gitinspector requires that the git executable is available in your PATH. \n"
                                       "Report gitinspector bugs to gitinspector@ejwa.se."))
    parser.add_argument('repositories', metavar='REPOSITORY', type=str, nargs='*',
                        help=_('the address of a repository to be analyzed'))
    parser.add_argument('-a', '--aliases', metavar='ALIASES', help=
                        _("a dictionary string indicating aliases for the authors"),
                        type=lambda s: ast.literal_eval(s), default={})
    parser.add_argument('-f', '--file-types', metavar='TYPES', help=
                        _("a comma separated list of file extensions to include when "
                          "computing statistics. The default extensions used are: ") + str(DEFAULT_EXTENSIONS) + " " +
                        _("Specifying * includes files with no extension, while ** includes all files"),
                        default=",".join(DEFAULT_EXTENSIONS))
    parser.add_argument('-F', '--format', metavar='FORMAT', help=
                        _("define in which format output should be generated; the "
                          "default format is 'text' and the available formats are: ") + str(__available_formats__),
                        default="text", choices=__available_formats__)
    parser.add_argument('-g', '--grading', action='store_true', help=
                        _("show statistics and information in a way that is formatted "
                          "for grading of student projects; this is the same as supplying "
                          "the options -HlmrTw"))
    parser.add_argument('-H', '--hard', action='store_true', help=
                        _("track rows and look for duplicates harder;"
                          "this can be quite slow with big repositories"))
    parser.add_argument('-l', '--list-file-types', action='store_true', help=
                        _("list all the file extensions available in the current branch "
                          "of the repository"))
    parser.add_argument('-L', '--localize-output', action='store_true', help=
                        _("localize the generated output to the selected "
                          "system language if a translation is available"))
    parser.add_argument('-m', '--metrics', action='store_true', help=
                        _("include checks for certain metrics during the analysis of commits"))
    parser.add_argument('-r', '--responsibilities', action='store_true', help=
                        _("show which files the different authors seem most responsible for"))
    parser.add_argument('-s', '--since', metavar='DATE',
                        type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d'), help=
                        _("only show statistics for commits more recent than a specific date, "
                          "specified as '%%Y-%%m-%%d'"),
                        default=None)
    parser.add_argument('-S', '--silent', action='store_true', help=
                        _("Silent output, mainly used for testing purposes"))
    parser.add_argument('-T', '--timeline', action='store_true', help=
                        _("show commit timeline, including author names"))
    parser.add_argument('-u', '--until', metavar='DATE',
                        type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d'), help=
                        _("only show statistics for commits older than a specific date, "
                          "specified as '%%Y-%%m-%%d'"),
                        default=None)
    parser.add_argument('-v', '--version', action='store_true', help=
                        _("display the current version of the program"))
    parser.add_argument('-w', '--weeks', action='store_true', help=
                        _("show all statistical information in weeks instead of in months"))
    parser.add_argument('-x', '--exclude', metavar='PATTERN', action='append', help=
                        _("an exclusion pattern of the form KEY=PAT, describing the file paths, "
                          "revisions, revisions with certain commit messages, author names or "
                          "author emails that should be excluded from the statistics; KEY must "
                          "be in [ 'file', 'author', 'email', 'revision', 'message' ]"))

    options = parser.parse_args() if args is None else parser.parse_args(args)
    options.progress = True  # Display progress messages

    if options.grading:
        options.metrics = True
        options.list_file_types = True
        options.responsibilities = True
        options.hard = True
        options.timeline = True
        options.weeks = True

    if options.exclude:
        for pat in options.exclude:
            filtering.add(pat)

    return options


def main():
    __check_python_version__()
    terminal.check_terminal_encoding()
    terminal.set_stdin_encoding()

    try:
        options = __parse_arguments__()

        if options.version:
            version.output()
            sys.exit(0)

        run = Runner(options, StdoutWriter())
        run.process()

    except (filtering.InvalidRegExpError, format.InvalidFormatError) as exception:
        print(sys.argv[0], "\b:", exception.msg, file=sys.stderr)
        print(_("Try `{0} --help' for more information.").
              format(sys.argv[0]), file=sys.stderr)
        sys.exit(2)


@atexit.register
def cleanup():
    Repository.delete_all()


if __name__ == "__main__":
    main()
