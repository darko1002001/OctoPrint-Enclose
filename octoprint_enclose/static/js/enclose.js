$(function () {
    function EncloseViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.loginState = parameters[1];

        self.settings = undefined;

        self.isPowerOn = ko.observable(undefined);
        self.powerIndicator = $("#enclosure-power-indicator");
        self.lightIndicator = $("#enclosure-light-indicator");

        self.onBeforeBinding = function () {
            self.settings = self.settingsViewModel.settings;
        };

        self.onStartup = function () {
            self.isPowerOn.subscribe(function (isPowerOn) {
                if (isPowerOn) {
                    self.powerIndicator.removeClass("off").addClass("on");
                } else {
                    self.powerIndicator.removeClass("on").addClass("off");
                }
            });
        };

         self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "enclose") {
                return;
            }

            self.isPowerOn(data.isPowerOn);
        };

        self.togglePower = function () {
            if (self.isPowerOn()) {
                self.turnPowerOff();
            } else {
                self.turnPowerOn();
            }
        };

        self.turnPowerOn = function () {
            $.ajax({
                url: API_BASEURL + "plugin/enclose",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "turnPowerOn"
                }),
                contentType: "application/json; charset=UTF-8"
            })
        };

        self.turnPowerOff = function () {
            $.ajax({
                url: API_BASEURL + "plugin/enclose",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "turnPowerOff"
                }),
                contentType: "application/json; charset=UTF-8"
            })
        };

        self.toggleLight = function () {
            $.ajax({
                url: API_BASEURL + "plugin/enclose",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "turnLightOn"
                }),
                contentType: "application/json; charset=UTF-8"
            })
        };

    }

    ADDITIONAL_VIEWMODELS.push([
        EncloseViewModel,
        ["settingsViewModel", "loginStateViewModel"],
        ["#navbar_plugin_enclose", "#settings_plugin_enclose"]
    ]);
});
