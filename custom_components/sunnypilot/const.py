"""Constants for the sunnypilot integration."""
from __future__ import annotations

DOMAIN = "sunnypilot"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_DEVICE_ID = "device_id"
UPDATE_INTERVAL = 30  # seconds

# platform: "switch" | "select" | "number"
# For select params, options list must be non-empty or the entity is skipped.
# Keys match the exact Sunnylink API param keys.
PARAM_REGISTRY: dict[str, dict] = {
    # ── Device ───────────────────────────────────────────────────────────────
    "OffroadMode": {
        "platform": "switch", "name": "Offroad Mode", "group": "device",
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
        "platform": "number", "name": "Max Time Offroad (min)", "group": "device",
        "min": 0, "max": 1440, "step": 1,
    },
    # ── Toggles ──────────────────────────────────────────────────────────────
    "OpenpilotEnabledToggle": {
        "platform": "switch", "name": "openpilot Enabled", "group": "toggles",
    },
    "LongitudinalPersonality": {
        "platform": "select", "name": "Driving Personality", "group": "toggles",
        "options": ["Relaxed", "Standard", "Aggressive"],
        "param_type": "Int",
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
        "platform": "switch", "name": "Always-on Driver Monitoring", "group": "toggles",
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
        "platform": "number", "name": "LAGD Delay (s)", "group": "toggles",
        "min": 0, "max": 10, "step": 1,
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
    "MadsMainCruiseAllowed": {
        "platform": "switch", "name": "MADS Main Cruise Allowed", "group": "steering",
    },
    "MadsUnifiedEngagementMode": {
        "platform": "switch", "name": "MADS Unified Engagement", "group": "steering",
    },
    "EnforceTorqueControl": {
        "platform": "switch", "name": "Enforce Torque Control", "group": "steering",
    },
    "CustomTorqueParams": {
        "platform": "switch", "name": "Custom Torque Params", "group": "steering",
    },
    "TorqueParamsOverrideEnabled": {
        "platform": "switch", "name": "Torque Override Enabled", "group": "steering",
    },
    "TorqueParamsOverrideLatAccelFactor": {
        "platform": "number", "name": "Lat Accel Factor", "group": "steering",
        "min": 0.0, "max": 5.0, "step": 0.01,
    },
    "TorqueParamsOverrideFriction": {
        "platform": "number", "name": "Friction Override", "group": "steering",
        "min": 0.0, "max": 2.0, "step": 0.01,
    },
    "LiveTorqueParamsToggle": {
        "platform": "switch", "name": "Live Torque Params", "group": "steering",
    },
    "LiveTorqueParamsRelaxedToggle": {
        "platform": "switch", "name": "Live Torque Params (Relaxed)", "group": "steering",
    },
    "BlinkerPauseLateralControl": {
        "platform": "switch", "name": "Pause Lateral on Blinker", "group": "steering",
    },
    "BlinkerMinLateralControlSpeed": {
        "platform": "number", "name": "Min Lateral Speed (blinker)", "group": "steering",
        "min": 0, "max": 100, "step": 1,
    },
    "AutoLaneChangeTimer": {
        "platform": "number", "name": "Auto Lane Change Timer (s)", "group": "steering",
        "min": 0, "max": 10, "step": 0.5,
    },
    "AutoLaneChangeBsmDelay": {
        "platform": "number", "name": "BSM Delay", "group": "steering",
        "min": 0, "max": 5, "step": 0.1,
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
        "platform": "switch", "name": "Hyundai Longitudinal Tuning", "group": "cruise",
    },
    "SpeedLimitValueOffset": {
        "platform": "number", "name": "Speed Offset Value", "group": "cruise",
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
        "platform": "number", "name": "Short Press Increment", "group": "cruise",
        "min": 1, "max": 20, "step": 1,
    },
    "CustomAccLongPressIncrement": {
        "platform": "number", "name": "Long Press Increment", "group": "cruise",
        "min": 1, "max": 20, "step": 1,
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
