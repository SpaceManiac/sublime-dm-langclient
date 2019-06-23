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


has_been_initialized = False
objtree_view = utils.HtmlView("dreammaker_object_tree", "DM Object Tree", "dm_internal_objtree")
objtree_root = None
expanded = set()


# Patch LSP get_initialize_params to include our capabilities
orig_initialize_params = sessions.get_initialize_params
def get_initialize_params(project_path, config):
	result = orig_initialize_params(project_path, config)
	if config.name == 'dm-langserver':
		capabilities = result.setdefault("capabilities", {})
		experimental = capabilities.setdefault("experimental", {})
		dreammaker = experimental.setdefault("dreammaker", {})
		dreammaker["objectTree"] = True
	print("capabilities patched")
	return result

sessions.get_initialize_params = get_initialize_params


def on_initialized(client):
	global has_been_initialized
	has_been_initialized = True
	client.on_notification('experimental/dreammaker/objectTree', on_object_tree)


def plugin_loaded():
	objtree_view.on_navigate = on_navigate
	objtree_view.reclaim_view()


def on_object_tree(message):
	global objtree_root
	objtree_root = message["root"]
	objtree_view.update(get_content())
	print("on_object_tree:", str(len(str(objtree_root))))


class DreammakerObjectTreeCommand(sublime_plugin.WindowCommand):
	def run(self, **kwargs):
		objtree_view.open_view(self.window, kwargs)


class DmInternalObjtreeCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		objtree_view.update(get_content())


class ObjtreeEventListener(sublime_plugin.EventListener):
	def on_close(self, view):
		objtree_view.on_close(view)


def on_navigate(href):
	if href.startswith('expand:'):
		expanded.add(href[len('expand:'):])
		objtree_view.update(get_content())
	elif href.startswith('contract:'):
		expanded.remove(href[len('contract:'):])
		objtree_view.update(get_content())


def get_content():
	if objtree_root is None:
		if has_been_initialized:
			return "Loading..."
		else:
			return "Tab to a .dm file and back to load the object tree."

	bits = []
	get_type_content(objtree_root, bits)
	return "".join(bits)


def get_type_content(ty, bits):
	bits.append(ty["name"])

	if ty["children"]:
		if ty["name"]:
			if ty["name"] in expanded:
				bits.append(" [<a href='contract:{}'>-{}</a>]".format(ty["name"], len(ty["children"])))
			else:
				bits.append(" [<a href='expand:{}'>+{}</a>]".format(ty["name"], len(ty["children"])))

		if not ty["name"] or ty["name"] in expanded:
			bits.append("<ul>")
			for child in ty["children"]:
				bits.append("<li>")
				get_type_content(child, bits)
				bits.append("</li>")
			bits.append("</ul>")


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