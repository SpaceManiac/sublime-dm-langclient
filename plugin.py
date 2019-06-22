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


def plugin_loaded():
	print("Extension path:", extension_path())
	Thread(target=prepare_server_thread).start()


def prepare_server_thread():
	cmd = determine_server_command()
	print("Command:", cmd)
	default_config.binary_args[0] = cmd


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
		self._name = default_name
		self._config = default_config

	@property
	def name(self) -> str:
		return self._name

	@property
	def config(self) -> ClientConfig:
		return self._config

	def on_start(self, window) -> bool:
		# Still waiting on prepare_server_thread to finish.
		if not default_config.binary_args[0]:
			# When we return False, it seems that LSP will call us again later,
			# so we have an opportunity to continue configuring.
			return False

		return True

	def on_initialized(self, client) -> None:
		print("on_initialized")
		pass # extra initialization here.

