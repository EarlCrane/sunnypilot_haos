"""Constants for the sunnypilot integration."""
from __future__ import annotations

DOMAIN = "sunnypilot"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_DEVICE_ID = "device_id"
UPDATE_INTERVAL = 15  # seconds

# platform: "switch" | "select" | "number"
# For select params, options list must be non-empty or the entity is skipped.
# Keys match the exact Sunnylink API param keys.
# Select options are ordered to match the integer index the API stores (0 = first option).
PARAM_REGISTRY: dict[str, dict] = {
    # ── Device Settings ───────────────────────────────────────────────────────
    "OffroadMode": {
        "platform": "switch", "name": "Offroad Mode", "group": "device",
    },
    "DeviceBootMode": {
        "platform": "select", "name": "Device Boot Mode", "group": "device",
        "options": ["Standard", "Always Offroad"], "param_type": "Int",
    },
    "IsMetric": {
        "platform": "switch", "name": "Metric Units", "group": "device",
    },
    "QuietMode": {
        "platform": "switch", "name": "Quiet Mode", "group": "device",
    },
    "OnroadUploads": {
        "platform": "switch", "name": "Onroad Uploads", "group": "device",
    },
    "RecordFront": {
        "platform": "switch", "name": "Record Front Camera", "group": "device",
    },
    "RecordAudio": {
        "platform": "switch", "name": "Record Audio", "group": "device",
    },
    "GsmMetered": {
        "platform": "switch", "name": "GSM Metered", "group": "device",
    },
    "GsmRoaming": {
        "platform": "switch", "name": "GSM Roaming", "group": "device",
    },
    "MaxTimeOffroad": {
        "platform": "number", "name": "Max Time Offroad", "group": "device",
        "min": 0, "max": 1440, "step": 1, "unit": "min",
    },
    # ── Toggles ──────────────────────────────────────────────────────────────
    "OpenpilotEnabledToggle": {
        "platform": "switch", "name": "openpilot Enabled", "group": "toggles",
    },
    "LongitudinalPersonality": {
        # 0=Relaxed, 1=Standard, 2=Aggressive (matches sunnypilot enum order)
        "platform": "select", "name": "Driving Personality", "group": "toggles",
        "options": ["Relaxed", "Standard", "Aggressive"], "param_type": "Int",
    },
    "IsLdwEnabled": {
        "platform": "switch", "name": "Lane Departure Warning", "group": "toggles",
    },
    "DisengageOnAccelerator": {
        "platform": "switch", "name": "Disengage on Accelerator", "group": "toggles",
    },
    "EnableWideCamera": {
        "platform": "switch", "name": "Wide Camera", "group": "toggles",
    },
    "AlwaysOnDM": {
        "platform": "switch", "name": "Always-on Driver Monitor", "group": "toggles",
    },
    "DisableLogging": {
        "platform": "switch", "name": "Disable Logging", "group": "toggles",
    },
    "DisableOnroadUploads": {
        "platform": "switch", "name": "Disable Onroad Uploads", "group": "toggles",
    },
    "DisablePowerDown": {
        "platform": "switch", "name": "Disable Power Down", "group": "toggles",
    },
    "DisableUpdates": {
        "platform": "switch", "name": "Disable Updates", "group": "toggles",
    },
    "SubaruStopAndGo": {
        "platform": "switch", "name": "Subaru Stop and Go", "group": "toggles",
    },
    "SubaruStopAndGoManualParkingBrake": {
        "platform": "switch", "name": "Subaru Manual Parking Brake", "group": "toggles",
    },
    "CameraOffset": {
        "platform": "number", "name": "Camera Offset", "group": "toggles",
        "min": -1.0, "max": 1.0, "step": 0.01,
    },
    "LagdToggle": {
        "platform": "switch", "name": "LAGD Toggle", "group": "toggles",
    },
    "LagdToggleDelay": {
        "platform": "number", "name": "LAGD Delay", "group": "toggles",
        "min": 0, "max": 10, "step": 1, "unit": "s",
    },
    "LaneTurnDesire": {
        "platform": "number", "name": "Lane Turn Desire", "group": "toggles",
        "min": 0.0, "max": 1.0, "step": 0.01,
    },
    "LaneTurnValue": {
        "platform": "number", "name": "Lane Turn Value", "group": "toggles",
        "min": 0.0, "max": 1.0, "step": 0.01,
    },
    # ── Steering ─────────────────────────────────────────────────────────────
    "Mads": {
        "platform": "switch", "name": "MADS Enabled", "group": "steering",
    },
    "MadsSteeringMode": {
        # 0=Remain Active, 1=Pause, 2=Disengage (from webarchive UI)
        "platform": "select", "name": "MADS Steering Mode", "group": "steering",
        "options": ["Remain Active", "Pause", "Disengage"], "param_type": "Int",
    },
    "MadsMainCruiseAllowed": {
        "platform": "switch", "name": "MADS Main Cruise Allowed", "group": "steering",
    },
    "MadsUnifiedEngagementMode": {
        "platform": "switch", "name": "MADS Unified Engagement", "group": "steering",
    },
    "EnforceTorqueControl": {
        "platform": "switch", "name": "Enforce Torque Control", "group": "steering",
    },
    "TorqueControlTune": {
        # 0=v0.0, 1=v1.0 (from webarchive: "Default: 0.0 Default v1.0 v0.0")
        "platform": "select", "name": "Torque Control Tune", "group": "steering",
        "options": ["v0.0", "v1.0"], "param_type": "Int",
    },
    "CustomTorqueParams": {
        "platform": "switch", "name": "Custom Torque Params", "group": "steering",
    },
    "TorqueParamsOverrideEnabled": {
        "platform": "switch", "name": "Torque Override Enabled", "group": "steering",
    },
    "TorqueParamsOverrideLatAccelFactor": {
        "platform": "number", "name": "Lat Accel Factor", "group": "steering",
        "min": 0.1, "max": 5.0, "step": 0.01,
    },
    "TorqueParamsOverrideFriction": {
        "platform": "number", "name": "Friction Override", "group": "steering",
        "min": 0.0, "max": 1.0, "step": 0.01,
    },
    "LiveTorqueParamsToggle": {
        "platform": "switch", "name": "Live Torque Self-Tune", "group": "steering",
    },
    "LiveTorqueParamsRelaxedToggle": {
        "platform": "switch", "name": "Live Torque Self-Tune (Relaxed)", "group": "steering",
    },
    "BlinkerPauseLateralControl": {
        "platform": "switch", "name": "Pause Lateral on Blinker", "group": "steering",
    },
    "BlinkerMinLateralControlSpeed": {
        "platform": "number", "name": "Min Lateral Speed (blinker)", "group": "steering",
        "min": 0, "max": 100, "step": 1,
    },
    "AutoLaneChangeTimer": {
        "platform": "number", "name": "Auto Lane Change Timer", "group": "steering",
        "min": 0, "max": 3, "step": 0.5, "unit": "s",
    },
    "AutoLaneChangeBsmDelay": {
        # UI shows as "Enabled/Disabled" boolean, not a numeric delay
        "platform": "switch", "name": "Auto Lane Change BSM Delay", "group": "steering",
    },
    "EnableHkgTuningAngleSmoothingFactor": {
        "platform": "switch", "name": "HKG Angle Smoothing", "group": "steering",
    },
    "HkgTuningOverridingCycles": {
        "platform": "number", "name": "HKG Overriding Cycles", "group": "steering",
        "min": 0, "max": 50, "step": 1,
    },
    "HkgTuningAngleActiveTorqueReductionGain": {
        "platform": "number", "name": "HKG Active Torque Reduction", "group": "steering",
        "min": 0.0, "max": 2.0, "step": 0.01,
    },
    "HkgTuningAngleMinTorqueReductionGain": {
        "platform": "number", "name": "HKG Min Torque Reduction", "group": "steering",
        "min": 0.0, "max": 2.0, "step": 0.01,
    },
    "HkgTuningAngleMaxTorqueReductionGain": {
        "platform": "number", "name": "HKG Max Torque Reduction", "group": "steering",
        "min": 0.0, "max": 2.0, "step": 0.01,
    },
    "NeuralNetworkLateralControl": {
        "platform": "switch", "name": "Neural Network Lateral Control", "group": "steering",
    },
    "TeslaCoopSteering": {
        "platform": "switch", "name": "Tesla Coop Steering", "group": "steering",
    },
    # ── Cruise ───────────────────────────────────────────────────────────────
    "AlphaLongitudinalEnabled": {
        "platform": "switch", "name": "Alpha Longitudinal", "group": "cruise",
    },
    "ExperimentalMode": {
        "platform": "switch", "name": "Experimental Mode", "group": "cruise",
    },
    "DynamicExperimentalControl": {
        "platform": "switch", "name": "Dynamic Experimental Control", "group": "cruise",
    },
    "HyundaiLongitudinalTuning": {
        # UI shows select: Off / Dynamic / Predictive (not a switch)
        "platform": "select", "name": "Hyundai Longitudinal Tuning", "group": "cruise",
        "options": ["Off", "Dynamic", "Predictive"], "param_type": "Int",
    },
    "SpeedLimitMode": {
        # 0=Off, 1=Information, 2=Warning, 3=Assist (from webarchive)
        "platform": "select", "name": "Speed Limit Assist Mode", "group": "cruise",
        "options": ["Off", "Information", "Warning", "Assist"], "param_type": "Int",
    },
    "SpeedLimitPolicy": {
        # 0=Car State Only, 1=Map Data Only, 2=Car State Priority, 3=Map Data Priority, 4=Combined
        "platform": "select", "name": "Speed Limit Source", "group": "cruise",
        "options": [
            "Car State Only", "Map Data Only",
            "Car State Priority", "Map Data Priority", "Combined",
        ], "param_type": "Int",
    },
    "SpeedLimitOffsetType": {
        # 0=Off, 1=Fixed, 2=Percentage (from webarchive)
        "platform": "select", "name": "Speed Limit Offset Type", "group": "cruise",
        "options": ["Off", "Fixed", "Percentage"], "param_type": "Int",
    },
    "SpeedLimitValueOffset": {
        "platform": "number", "name": "Speed Limit Offset", "group": "cruise",
        "min": -30, "max": 30, "step": 1,
    },
    "SmartCruiseControlVision": {
        "platform": "switch", "name": "Vision SCC", "group": "cruise",
    },
    "SmartCruiseControlMap": {
        "platform": "switch", "name": "Map SCC", "group": "cruise",
    },
    "IntelligentCruiseButtonManagement": {
        "platform": "switch", "name": "Intelligent Cruise Buttons", "group": "cruise",
    },
    "CustomAccIncrementsEnabled": {
        "platform": "switch", "name": "Custom ACC Increments", "group": "cruise",
    },
    "CustomAccShortPressIncrement": {
        # UI shows range 1-10 (not 1-20 as originally assumed)
        "platform": "number", "name": "Short Press Increment", "group": "cruise",
        "min": 1, "max": 10, "step": 1,
    },
    "CustomAccLongPressIncrement": {
        # UI shows range 1-10, default 5
        "platform": "number", "name": "Long Press Increment", "group": "cruise",
        "min": 1, "max": 10, "step": 1,
    },
    # ── Developer ────────────────────────────────────────────────────────────
    "SshEnabled": {
        "platform": "switch", "name": "SSH", "group": "developer",
    },
    "AdbEnabled": {
        "platform": "switch", "name": "ADB", "group": "developer",
    },
    "EnableSunnylinkUploader": {
        "platform": "switch", "name": "Sunnylink Uploader", "group": "developer",
    },
    "ShowAdvancedControls": {
        "platform": "switch", "name": "Show Advanced Controls", "group": "developer",
    },
    "QuickBootToggle": {
        "platform": "switch", "name": "Quick Boot", "group": "developer",
    },
    "EnableCopyparty": {
        "platform": "switch", "name": "Enable Copyparty", "group": "developer",
    },
    "JoystickDebugMode": {
        "platform": "switch", "name": "Joystick Debug Mode", "group": "developer",
    },
    "EnableGithubRunner": {
        "platform": "switch", "name": "GitHub Runner", "group": "developer",
    },
    "GithubRunnerSufficientVoltage": {
        "platform": "switch", "name": "Runner Voltage Check", "group": "developer",
    },
}

ALL_PARAM_KEYS: list[str] = list(PARAM_REGISTRY.keys())
