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

# HTML view for the DreamMaker object tree.

import sublime, sublime_plugin

from LSP.plugin.core import sessions

from . import utils

try:
	from . import reference_browser
except ImportError:
	reference_browser = None


has_been_initialized = False
objtree_root = None
expanded = set()


def plugin_loaded():
	ObjtreeView.instance = ObjtreeView()


def on_initialized(client):
	global has_been_initialized
	has_been_initialized = True
	client.on_notification('experimental/dreammaker/objectTree', on_object_tree)


def on_object_tree(message):
	global objtree_root
	objtree_root = message["root"]
	ObjtreeView.instance.update()


class DreammakerObjectTreeCommand(sublime_plugin.WindowCommand):
	def run(self):
		ObjtreeView.instance.open_view(self.window)


class ObjtreeEventListener(sublime_plugin.EventListener):
	def on_close(self, view):
		ObjtreeView.instance.on_close(view)


class ObjtreeView(utils.HtmlView):
	instance = None
	phantom_set_key = "dreammaker_object_tree"
	name = "DM Object Tree"

	def on_navigate(self, href):
		if href.startswith('expand:'):
			expanded.add(href[len('expand:'):])
			self.update()

		elif href.startswith('contract:'):
			expanded.remove(href[len('contract:'):])
			self.update()

		elif href.startswith('dmref:'):
			self.view.window().run_command("dreammaker_open_reference", {"dm_path": href[len('dmref:'):]})

		elif href.startswith('file:'):
			fname = href[len('file:'):]
			# It would make sense to use sublime.TRANSIENT here, but there appears
			# to be a bug where transient windows are never "opened" onto the
			# langserver, even when they are first modified.
			self.view.window().open_file(fname, sublime.ENCODED_POSITION)

	def get_content(self):
		if objtree_root is None:
			if has_been_initialized:
				return "Loading..."
			else:
				return "Open a .dm file to load the object tree."

		bits = ["""<style>
			a {text-decoration: none;}
			.expand, .contract {color: lightblue;}
			.go {color: white;}
			.nolink {color: red;}
			</style>"""]
		get_type_content(objtree_root, bits)
		return "".join(bits)


def get_type_content(ty, bits):
	if ty["name"]:
		if ty["children"]:
			if ty["name"] in expanded:
				bits.append("<a class='contract' href='contract:{}'>--</a> ".format(ty["name"], len(ty["children"])))
			else:
				bits.append("<a class='expand' href='expand:{}'>++</a> ".format(ty["name"], len(ty["children"])))
		else:
			bits.append("&nbsp;&nbsp;&nbsp;")

	link = location_to_href(ty["location"])
	if link:
		bits.append("<a class='go' href='{}'>{}</a>".format(link, ty["name"]))
	else:
		bits.append("<span class='nolink'>{}</a>".format(ty["name"]))

	if ty["children"] and (not ty["name"] or ty["name"] in expanded):
		bits.append("<ul>")
		for child in ty["children"]:
			bits.append("<li>")
			get_type_content(child, bits)
			bits.append("</li>")
		bits.append("</ul>")


def location_to_href(location):
	if location["uri"].startswith("file:///"):
		return "file:{}:{}:{}".format(
			location["uri"][len("file://"):],
			location["range"]["start"]["line"],
			location["range"]["start"]["character"])
	elif location["uri"].startswith("dm://docs/reference.dm#") and reference_browser:
		return "dmref:{}".format(location["uri"][len("dm://docs/reference.dm#"):])


# export interface ObjectTreeParams {
#     root: ObjectTreeType,
# }
# export interface ObjectTreeEntry {
#     name: string,
#     kind: SymbolKind,
#     location: Location | undefined,
# }
# export interface ObjectTreeType extends ObjectTreeEntry {
#     vars: ObjectTreeVar[],
#     procs: ObjectTreeProc[],
#     children: ObjectTreeType[],
# }
# export interface ObjectTreeVar extends ObjectTreeEntry {
#     is_declaration: boolean,
# }
# export interface ObjectTreeProc extends ObjectTreeEntry {
#     is_verb: boolean | undefined,
# }
