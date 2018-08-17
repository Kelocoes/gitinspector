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

import string
import textwrap
from .. import extensions, terminal
from .outputable import Outputable


EXTENSIONS_INFO_TEXT = lambda: _("The extensions below were found in the repository history")
EXTENSIONS_MARKED_TEXT = lambda: _("(extensions used during statistical analysis are marked)")

class ExtensionsOutput(Outputable):
    output_order = 700

    def __init__(self, runner):
        Outputable.__init__(self)
        self.display = bool(runner.changes.commits) and bool(runner.config.list_file_types)
        self.out = runner.out

    @staticmethod
    def is_marked(extension):
        if extension in extensions.__extensions__ or "**" in extensions.__extensions__:
            return True

        return False

    def output_html(self):
        extensions_str = ""
        for i in sorted(extensions.__located_extensions__):
            if ExtensionsOutput.is_marked(i):
                extensions_str += "<strong>" + i + "</strong>"
            else:
                extensions_str += i
            extensions_str += " "

        with open("gitinspector/templates/extensions_output.html", 'r') as infile:
            src = string.Template( infile.read() )
            self.out.write(src.substitute(
                extensions_info_text=EXTENSIONS_INFO_TEXT(),
                extensions_marked_text=EXTENSIONS_MARKED_TEXT(),
                extensions=extensions_str,
            ))

    def output_json(self):
        if extensions.__located_extensions__:
            message_json = "\t\t\t\"message\": \"" + EXTENSIONS_INFO_TEXT() + "\",\n"
            used_extensions_json = ""
            unused_extensions_json = ""

            for i in sorted(extensions.__located_extensions__):
                if ExtensionsOutput.is_marked(i):
                    used_extensions_json += "\"" + i + "\", "
                else:
                    unused_extensions_json += "\"" + i + "\", "

            used_extensions_json = used_extensions_json[:-2]
            unused_extensions_json = unused_extensions_json[:-2]

            self.out.write(",\n\t\t\"extensions\": {\n" + message_json + "\t\t\t\"used\": [ " +
                           used_extensions_json + " ],\n\t\t\t\"unused\": [ " +
                           unused_extensions_json + " ]\n" + "\t\t}")

    def output_text(self):
        if extensions.__located_extensions__:
            self.out.writeln("\n" +
                             textwrap.fill("{0} {1}:".format(EXTENSIONS_INFO_TEXT(),
                                                             EXTENSIONS_MARKED_TEXT()),
                                           width=terminal.get_size()[0]))

            for i in sorted(extensions.__located_extensions__):
                if ExtensionsOutput.is_marked(i):
                    self.out.write("[" + terminal.__bold__ + i + terminal.__normal__ + "] ")
                else:
                    self.out.write(i + " ")

    def output_xml(self):
        if extensions.__located_extensions__:
            message_xml = "\t\t<message>" + EXTENSIONS_INFO_TEXT() + "</message>\n"
            used_extensions_xml = ""
            unused_extensions_xml = ""

            for i in sorted(extensions.__located_extensions__):
                if ExtensionsOutput.is_marked(i):
                    used_extensions_xml += "\t\t\t<extension>" + i + "</extension>\n"
                else:
                    unused_extensions_xml += "\t\t\t<extension>" + i + "</extension>\n"

            self.out.writeln("\t<extensions>\n" + message_xml + "\t\t<used>\n" +
                             used_extensions_xml + "\t\t</used>\n" +
                             "\t\t<unused>\n" + unused_extensions_xml +
                             "\t\t</unused>\n" + "\t</extensions>")
