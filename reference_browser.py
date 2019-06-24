# DreamMaker Language Client - Sublime package for DreamMaker Language Server
# Copyright (C) 2019  Tad Hardesty
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File system provider which serves HTML excerpts from the BYOND reference.

import re

import sublime, sublime_plugin

from . import utils


class RefView(utils.HtmlView):
    phantom_set_key = "dreammaker_reference"
    name = "DM Reference"

    def get_content(self, dm_path=None):
        return get_content(dm_path)

    def on_navigate(self, href):
        return on_navigate(href)


ref_view = None


def plugin_loaded():
    global ref_view
    ref_view = RefView()


class DreammakerOpenReferenceCommand(sublime_plugin.WindowCommand):
    def run(self, dm_path=None):
        view = ref_view.open_view(self.window, dm_path=dm_path)
        view.show(0)


class ReferenceEventListener(sublime_plugin.EventListener):
    def on_close(self, view):
        ref_view.on_close(view)


def on_navigate(href):
    if href.startswith('info.html#'):
        rest = href[len('info.html#'):]
        sublime.active_window().run_command('dreammaker_open_reference', {"dm_path": rest})
    elif href.startswith('#'):
        rest = href[1:]
        sublime.active_window().run_command('dreammaker_open_reference', {"dm_path": rest})
    elif href == "command:dreammaker.openReference":
        sublime.active_window().run_command('dreammaker_open_reference')


def get_content(dm_path):
    if dm_path:
        fname = utils.find_byond_file(['help/ref/info.html'])
        if not fname:
            sublime.error_message("A valid Windows BYOND path must be given to use the reference browser.")
            utils.open_settings()
            return

        with open(fname, encoding='latin1') as f:
            contents = f.read()

        dm_path = dm_path.replace(">", "&gt;").replace("<", "&lt;")

        # Extract the section for the item being looked up
        start = contents.find("<a name={}>".format(dm_path))
        if start < 0:
            # Handle @dt; and @qu;
            start = contents.find("<a name={} toc=".format(dm_path))
            dm_path = dm_path.replace("@dt;", ".").replace("@qu;", '?')
        if start < 0:
            # Handle constants which are subordinate to another entry
            raw_name = dm_path[1 + dm_path.rfind("/"):]
            start = contents.find(raw_name)
            start = contents.find("<a name=", start)
        if start < 0:
            body = "No such entry <tt>{}</tt> in the reference.".format(dm_path)
        else:
            start = contents.find("\n", start)
            end = contents.find("<hr", start)
            body = contents[start:end]
    else:
        fname = utils.find_byond_file(['help/ref/contents.html'])
        if not fname:
            sublime.error_message("A valid Windows BYOND path must be given to use the reference browser.")
            utils.open_settings()
            return

        with open(fname, encoding='latin1') as f:
            contents = f.read()

        body = contents[contents.index("<dl>"):contents.index("</body>")]

    body = body.replace("<dd><dl>", "<dl>")
    body = body.replace("<dl><dt>", "<ul><li>")
    body = body.replace("<dl>", "<ul><li>")
    body = body.replace("</dl>", "</li></ul>")
    body = body.replace("<dd>", "</li><li>")
    body = body.replace("<dt>", "</li><li>")
    body = body.replace("</dd>", "")
    body = body.replace("</dt>", "")
    body = body.replace("<xmp>", "<pre>")
    body = body.replace("</xmp>", "</pre>")
    body = re.sub(r'(<li>\s*)+', r'<li>', body)
    body = re.sub(r'(</li>\s*)+', r'</li>', body)
    body = re.sub(r'<a href=([^>]+)>', r'<a href="\1">', body)
    body = body.replace("<<", "&lt;&lt;")
    body = re.sub(r'<([^/a-zA-Z])', r'&lt;\1', body)
    body = re.sub(r'&([^&#a-z])', r'&amp;\1', body)
    body = re.sub(r'<li>\s*</li>', r'', body)
    body = pre(body)

    return format_body(body, dm_path)


def pre(body):
    output = ''
    last_pos = 0
    while True:
        start = body.find('<pre>', last_pos)
        if start < 0:
            output += body[last_pos:]
            break
        output += body[last_pos:start]
        end = body.find('</pre>', start)
        if end < 0:
            break
        output += body[start + len('<pre>'):end].replace("\n", "<br>")
        last_pos = end + len('</pre>')
    return output


def format_body(body, dm_path=None):
        return """<!DOCTYPE html>
<html>
<head>
</head>
<body id="dm-reference">
<div style='margin-bottom:10px; background: rgba(128,128,128,0.2);'>
<b><tt>{dm_path}</tt></b> |
<a href="command:dreammaker.openReference">Index</a> |
<a href="https://secure.byond.com/docs/ref/index.html#{dm_path}">Online</a>
</div>
{body}
</body>
</html>""".format(dm_path=dm_path or "/", body=body)
