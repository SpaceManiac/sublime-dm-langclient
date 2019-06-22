import shutil

import os
import stat
import sublime
import sublime_plugin
from threading import Thread
from LSP.plugin.core.handlers import LanguageHandler
from LSP.plugin.core.settings import ClientConfig, LanguageConfig

from .dmlc.utils import extension_path
from .dmlc.findserver import determine_server_command

default_name = 'dreammaker'
server_package_name = 'vscode-css-languageserver-bin'
PKG_FOLDER = "DreamMaker Language Client"

default_config = ClientConfig(
	name=default_name,
	binary_args=[None],
	tcp_port=None,
	enabled=True,
	init_options=dict(),
	settings=dict(),
	env=dict(),
	languages=[
		LanguageConfig(
			'dreammaker',
			['source.dm'],
			["Packages/" + PKG_FOLDER + "/dreammaker.tmLanguage"]
		),
	]
)


def prepare_server_thread():
	print("in prepare_server_thread")
	cmd = determine_server_command()
	print("determined:", cmd)
	default_config.binary_args[0] = cmd


def plugin_loaded():
	print("Extension path:", extension_path())
	print(os.path.join(os.getcwd(), "Packages", PKG_FOLDER))

	Thread(target=prepare_server_thread).start()
	pass

	# // prepare the status bar
	# status = window.createStatusBarItem(StatusBarAlignment.Left, 10);
	# status.text = "DM: starting";
	# status.command = 'dreammaker.restartLangserver';
	# status.show();

	# ticked_status = window.createStatusBarItem(StatusBarAlignment.Right, 100);
	# ticked_status.command = 'dreammaker.toggleTicked';
	# context.subscriptions.push(window.onDidChangeActiveTextEditor(update_ticked_status));
	# update_ticked_status();


###############################################################################
# LSP Integration

class LspDreammakerPlugin(LanguageHandler):
	def __init__(self):
		print("langhandler __init__")
		self._name = default_name
		self._config = default_config

	@property
	def name(self) -> str:
		print("langhandler name()")
		return self._name

	@property
	def config(self) -> ClientConfig:
		print("langhandler config()")
		return self._config

	def on_start(self, window) -> bool:
		print("on_start", default_config.binary_args)

		# still waiting on server
		if not default_config.binary_args[0]:
			return False

		return True

	def on_initialized(self, client) -> None:
		print("on_initialized")
		pass # extra initialization here.

