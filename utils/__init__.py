# 'utils' package
import os
import sublime
import hashlib

from threading import Condition


def md5_file(path):
	h = hashlib.new('md5')
	with open(path, 'rb') as f:
		h.update(f.read())
	return h.hexdigest()


def extension_path():
	return os.path.split(os.path.split(__file__)[0])[0]


def get_config(name, default=None):
	return sublime.load_settings("dreammaker.sublime-settings").get("dreammaker." + name, default)


def set_config(name, value):
	return sublime.load_settings("dreammaker.sublime-settings").set("dreammaker." + name, value)


class Promise():
	def __init__(self):
		self.cv = Condition()

	def notify(self, *args):
		with self.cv:
			self.result = args
			self.cv.notify()

	def wait(self):
		with self.cv:
			self.cv.wait()
			return self.result
