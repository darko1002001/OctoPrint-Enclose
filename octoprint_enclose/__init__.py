# coding=utf-8
from __future__ import absolute_import
from octoprint_enclose.timer import *
from gpiozero import Button

import octoprint.plugin
import RPi.GPIO as GPIO

import requests
from flask import make_response, jsonify
from octoprint.server import user_permission


class EnclosePlugin(octoprint.plugin.StartupPlugin,
					octoprint.plugin.ProgressPlugin,
					octoprint.plugin.EventHandlerPlugin,
					octoprint.plugin.SettingsPlugin,
					octoprint.plugin.AssetPlugin,
					octoprint.plugin.SimpleApiPlugin,
					octoprint.plugin.TemplatePlugin):
	TIMER_DURATION = 60 * 3

	def __init__(self):
		self.timer = None
		self.isPowerOn = False
		self.enclosureGPIOButtonPin = 0
		self.powerGPIOButtonPin = 0
		self.powerGPIORelayPin = 0

	def on_after_startup(self):
		self._logger.info("OctoEnclosure (on host: %s)" % self._settings.get(["hostname"]))

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self.powerGPIORelayPin, GPIO.OUT)
		GPIO.output(self.powerGPIORelayPin, GPIO.LOW)

		button_enclosure = Button(self.enclosureGPIOButtonPin, hold_time=2)
		button_power = Button(self.powerGPIOButtonPin, hold_time=2)
		button_enclosure.when_held = self.enclosure_callback
		button_power.when_held = self.power_callback

	def get_settings_defaults(self):
		return dict(
			hostname="",
			enclosureGPIOButtonPin=18,
			powerGPIOButtonPin=23,
			powerGPIORelayPin=4
		)

	def on_settings_initialized(self):
		self.enclosureGPIOButtonPin = self._settings.get_int(["enclosureGPIOButtonPin"])
		self.powerGPIOButtonPin = self._settings.get_int(["powerGPIOButtonPin"])
		self.powerGPIORelayPin = self._settings.get_int(["powerGPIORelayPin"])

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
					   octoprint.events.Events.PRINT_CANCELLED,
					   octoprint.events.Events.PRINT_PAUSED,
					   octoprint.events.Events.PRINT_RESUMED]:
			self._logger.info("event action needed %s" % event)
			self.execute_request("ledOn?r=800&g=800&b=800")
			self.stop_timer()
		elif event in [octoprint.events.Events.PRINT_FAILED]:
			self._logger.info("event error %s" % event)
			self.execute_request("ledOn?r=1023&g=500&b=500")
			self.stop_timer()
		else:
			self._logger.info("event received %s" % event)

	def execute_request(self, path):
		try:
			hostname = self._settings.get(["hostname"])
			url = "%s/%s" % (hostname, path)
			if hostname:
				self._logger.info("fetching data: %s)" % url)
				r = requests.get(url)
				self._logger.info("Response status: %s)" % r.status_code)
		except Exception as ex:
			self.log_error(ex)

	def enclosure_callback(self, channel):
		self._logger.info("Light button pressed")
		self.turn_light_on()

	def power_callback(self, channel):
		self._logger.info("Power button pressed")
		self.toggle_power()

	def toggle_power(self):
		self._logger.info("Toggling power")
		if self.isPowerOn:
			self.turn_power_off()
		else:
			self.turn_power_on()

	def turn_power_on(self):
		self._logger.info("Turning power on")
		GPIO.output(self.powerGPIORelayPin, GPIO.HIGH)
		self.isPowerOn = True
		self.send_ui_event()

	def turn_power_off(self):
		self._logger.info("Turning power off")
		GPIO.output(self.powerGPIORelayPin, GPIO.LOW)
		self.isPowerOn = False
		self.send_ui_event()

	def turn_light_on(self):
		self._logger.info("Turning enclosure lights on")
		self.execute_request("ledOn?r=1023&g=1023&b=1023")
		self.execute_request("fanOn")

	def get_api_commands(self):
		return dict(
			turnPowerOn=[],
			turnPowerOff=[],
			togglePower=[],
			getPowerState=[],
			turnLightOn=[]
		)

	def on_api_command(self, command, data):
		if not user_permission.can():
			return make_response("Insufficient rights", 403)

		if command == 'turnPowerOn':
			if not self.isPowerOn:
				self.turn_psu_on()
		elif command == 'turnPowerOff':
			if self.isPowerOn:
				self.turn_psu_off()
		elif command == 'togglePower':
			self.toggle_power()
		elif command == 'turnLightOn':
			self.turn_light_on()
		elif command == 'getPowerState':
			return jsonify(isPowerOn=self.isPowerOn)

	def send_ui_event(self):
		self._plugin_manager.send_plugin_message(self._identifier, dict(isPowerOn=self.isPowerOn))

	def log_error(self, ex):
		template = "An exception of type {0} occurred on {1}. Arguments:\n{2!r}"
		message = template.format(
			type(ex).__name__, inspect.currentframe().f_code.co_name, ex.args)
		self._logger.warn(message)

	def get_assets(self):
		return dict(
			js=["js/enclose.js"],
			css=["css/enclose.css"]
		)

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
