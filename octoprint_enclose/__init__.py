# coding=utf-8
from __future__ import absolute_import
from octoprint_enclose.timer import *

import octoprint.plugin

import requests


class EnclosePlugin(octoprint.plugin.StartupPlugin,
					octoprint.plugin.ProgressPlugin,
					octoprint.plugin.EventHandlerPlugin,
					octoprint.plugin.SettingsPlugin,
					octoprint.plugin.TemplatePlugin):
	TIMER_DURATION = 60 * 3

	def __init__(self):
		self.timer = None

	def on_after_startup(self):
		self._logger.info("OctoEnclosure (on host: %s)" % self._settings.get(["hostname"]))

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			hostname=""
		)

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False)
		]

	def get_template_vars(self):
		return dict(
		)

	def keep_alive(self):
		self._logger.info("OctoEnclosure keeping alive")
		self.execute_request("keepAlive")

	def start_timer(self):
		self.stop_timer()
		self.timer = Timer(EnclosePlugin.TIMER_DURATION, self.keep_alive)
		self.timer.start()

	def stop_timer(self):
		if self.timer:
			self.timer.cancel()
			self.timer = None

	def on_print_progress(self, storage, path, progress):
		self._logger.info("OctoEnclosure print progress: %s)" % progress)
		self.keep_alive()

	def on_event(self, event, payload):
		if event == octoprint.events.Events.PRINT_STARTED:
			self._logger.info("print started  %s)" % event)
			self.execute_request("ledOn?r=1023&g=1023&b=1023")
			self.execute_request("fanOn")
			self.start_timer()
		elif event == octoprint.events.Events.PRINT_DONE:
			self._logger.info("print done %s)" % event)
			self.execute_request("ledOn?r=200&g=1023&b=200")
			self.stop_timer()
		elif event in [octoprint.events.Events.CONNECTED,
					   octoprint.events.Events.DISCONNECTED,
					   octoprint.events.Events.PRINT_CANCELLED,
					   octoprint.events.Events.PRINT_PAUSED,
					   octoprint.events.Events.PRINT_RESUMED]:
			self._logger.info("event action needed %s" % event)
			self.execute_request("ledOn?r=800&g=800&b=800")
			self.stop_timer()
		elif event in [octoprint.events.Events.PRINT_FAILED,
					   octoprint.events.Events.ERROR]:
			self._logger.info("event error %s" % event)
			self.execute_request("ledOn?r=1023&g=200&b=200")
			self.stop_timer()
		else:
			self._logger.info("event received %s" % event)

	def execute_request(self, path):
		url = ""
		try:
			hostname = self._settings.get(["hostname"])
			url = "%s/%s" % (hostname, path)
			if hostname:
				self._logger.info("fetching data: %s)" % url)
				r = requests.get(url)
				self._logger.info("Response status: %s)" % r.status_code)
		except:
			self._logger.info("Error executing request: %s)" % url)

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			enclose=dict(
				displayName="Enclose Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="darko1002001",
				repo="OctoPrint-Enclose",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/darko1002001/OctoPrint-Enclose/archive/{target_version}.zip"
			)
		)


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = EnclosePlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
