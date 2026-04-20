# sunnypilot for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Control and monitor your [sunnypilot](https://github.com/sunnyhaibin/sunnypilot) device from Home Assistant. Toggle driving modes, adjust cruise and steering settings, and build dashboards or automations around SunnyLink-backed settings.

---

## What it does

- Exposes **67 sunnypilot parameters** as native Home Assistant entities
- **49 switches** — one-tap toggles for features like Experimental Mode, MADS, openpilot Enabled, SSH, and more
- **17 number sliders** — numeric controls for offsets, timers, and tuning gains
- **1 select** — Driving Personality (Relaxed / Standard / Aggressive)
- Polls the SunnyLink API every 15 seconds to reflect current device state
- Changes take effect immediately on write; state refreshes after each action
- Includes a ready-made Lovelace dashboard YAML
- Installable through HACS as a custom repository

Current status:
- Working for my comma 4 / sunnypilot setup
- Early community-maintained project
- SunnyLink polling is cloud-based, so it depends on SunnyLink authentication and API behavior
- Not affiliated with or maintained by sunnypilot, comma, or Home Assistant

Next Steps:
- Get Alexa working for in-car commands
- Improve the auth so you don't have to dig up the token from developer mode
- Local SSH login to Copyparty to download drives through HAOS

---

## Requirements

- Home Assistant 2024.1.0 or later
- A [sunnypilot](https://github.com/sunnyhaibin/sunnypilot) device with a Sunnylink account
- Sunnylink login via GitHub or Google (device flow — no password needed)
- [HACS](https://hacs.xyz/) installed in Home Assistant

---

## Installation

### 1. Make sure HACS is installed
If you haven't installed HACS yet, follow the [HACS installation guide](https://hacs.xyz/docs/setup/download/).

### 2. Add this repository to HACS
1. Open HACS in Home Assistant
2. Click the **⋮** menu (top right) → **Custom repositories**
3. Enter the repository URL:
   ```
   https://github.com/EarlCrane/sunnypilot_haos
   ```
4. Set category to **Integration**
5. Click **Add**

### 3. Install the integration
1. In HACS → **Integrations**, search for **sunnypilot**
2. Click **Download** and confirm
3. **Restart Home Assistant**

### 4. Add the integration
1. Go to **Settings → Integrations → + Add Integration**
2. Search for **sunnypilot**
3. A setup screen will appear with a URL and a short code

---

## Configuration

### Authorization

sunnypilot uses your SunnyLink account credentials. You'll need to provide a **refresh token** from your SunnyLink session. This is a one-time setup step — the integration refreshes the token automatically from then on.

#### How to get your refresh token

1. Open [sunnylink.ai](https://www.sunnylink.ai) in a desktop browser and log in with GitHub or Google
2. Open DevTools:
   - **Chrome/Edge**: `F12` or `Cmd+Option+I` (Mac)
   - **Safari**: Enable Developer Tools in Preferences → Advanced, then `Cmd+Option+I`
3. Go to **Application** tab → **Local Storage** → `https://www.sunnylink.ai`
4. Look for a key containing `refresh_token` — it may be nested inside a JSON value under a key like `logto:storage` or similar
5. Copy the refresh token value (a long string starting with a random character sequence)

Do not share your refresh token, browser local storage, HAR files, Home Assistant config entries, or captured SunnyLink API payloads. They may grant access to your SunnyLink account or device settings.

#### Entering the token in Home Assistant

When you add the integration, paste the refresh token into the **Refresh Token** field. Home Assistant will validate it, then auto-detect your device.

Tokens are refreshed automatically in the background. You should only need to do this once.

### Device selection

If your account has multiple sunnypilot devices, you'll be prompted to choose one. If you have only one device, it's selected automatically.

### Settings storage

The integration stores your refresh token in Home Assistant's config entry storage. Treat Home Assistant backups and `.storage` files as sensitive.

---

## Entities

Entities are grouped by the same navigation categories used in sunnypilot itself:

### Device
| Entity | Type | Description |
|--------|------|-------------|
| Offroad Mode | Switch | Put device in offroad mode |
| Metric Units | Switch | Use metric units |
| Quiet Mode | Switch | Suppress sounds |
| Onroad Uploads | Switch | Allow uploads while driving |
| Record Front Camera | Switch | Record front-facing camera |
| Record Audio | Switch | Record microphone audio |
| GSM Metered | Switch | Treat cellular as metered |
| GSM Roaming | Switch | Allow GSM roaming |
| Max Time Offroad | Number | Minutes before auto power-down (0–1440) |

### Toggles
| Entity | Type | Description |
|--------|------|-------------|
| openpilot Enabled | Switch | Master enable for openpilot |
| Driving Personality | Select | Relaxed / Standard / Aggressive |
| Lane Departure Warning | Switch | LDW alerts |
| Disengage on Accelerator | Switch | Disengage when accelerator pressed |
| Wide Camera | Switch | Use wide-angle camera |
| Always-on Driver Monitoring | Switch | DM active even when disengaged |
| Disable Logging | Switch | Stop local log recording |
| Disable Onroad Uploads | Switch | Block uploads while driving |
| Disable Power Down | Switch | Prevent auto power-off |
| Disable Updates | Switch | Block OTA updates |
| LAGD Toggle | Switch | Lane-assist guided driving |
| Camera Offset | Number | Lateral camera correction (−1.0 to 1.0) |

### Steering
| Entity | Type | Description |
|--------|------|-------------|
| MADS Enabled | Switch | Modified Assistive Driving Safety |
| MADS Main Cruise Allowed | Switch | Allow MADS with main cruise |
| MADS Unified Engagement | Switch | Unified engagement mode |
| Enforce Torque Control | Switch | Force torque-based lateral control |
| Live Torque Params | Switch | Use live-learned torque parameters |
| Pause Lateral on Blinker | Switch | Suspend lane keep when signaling |
| Neural Network Lateral Control | Switch | NN-based steering model |
| Tesla Coop Steering | Switch | Tesla cooperative steering |
| Auto Lane Change Timer | Number | Seconds before auto lane change (0–10) |
| Lat Accel Factor | Number | Torque override lateral accel factor |

### Cruise
| Entity | Type | Description |
|--------|------|-------------|
| Experimental Mode | Switch | Enable experimental longitudinal control |
| Dynamic Experimental Control | Switch | Auto-switch to experimental when safe |
| Alpha Longitudinal | Switch | Alpha longitudinal control model |
| Vision SCC | Switch | Vision-based smart cruise control |
| Map SCC | Switch | Map-based smart cruise control |
| Intelligent Cruise Buttons | Switch | Smart cruise button management |
| Custom ACC Increments | Switch | Custom speed increment sizes |
| Speed Offset Value | Number | Speed limit offset (−30 to +30) |

### Developer
| Entity | Type | Description |
|--------|------|-------------|
| SSH | Switch | Enable SSH access |
| ADB | Switch | Enable ADB debugging |
| Sunnylink Uploader | Switch | Enable Sunnylink data uploader |
| Quick Boot | Switch | Skip boot animation |
| Enable Copyparty | Switch | Enable Copyparty file server |
| Joystick Debug Mode | Switch | Joystick input for debugging |
| GitHub Runner | Switch | Enable self-hosted GitHub Actions runner |

---

## Alexa integration

Voice control is a next step. With a [Nabu Casa](https://www.nabucasa.com/) subscription, selected switch entities can be exposed to Amazon Alexa. This may also work from in-car Alexa on supported vehicles because Alexa follows your Amazon account across devices.

**Example voice commands:**
- *"Alexa, turn on Experimental Mode"*
- *"Alexa, turn off openpilot"*
- *"Alexa, turn on Offroad Mode"*

For select controls (like Driving Personality), create an HA Script for each option and expose it as a scene:
- *"Alexa, turn on Relaxed Driving Mode"* → script sets personality to Relaxed

Only expose entities you are comfortable controlling by voice. Some sunnypilot settings affect driving behavior.

---

## Dashboard

A ready-made Lovelace dashboard with all five tabs (Device, Toggles, Steering, Cruise, Developer) is included in the repository as `lovelace_dashboard.yaml`.

To import it:
1. Settings → Dashboards → **+ Add Dashboard**
2. Choose **"From YAML"** and paste the contents of `lovelace_dashboard.yaml`

> **Note:** Entity IDs are auto-generated by Home Assistant from the entity names. If any IDs don't match, use Developer Tools → States to find the correct IDs and update the YAML.

---

## Troubleshooting

**Integration not found after install**
Restart Home Assistant after downloading from HACS.

**Authorization code expired**
The code is valid for ~10 minutes. Remove the integration and add it again to get a new code.

**Entities show "unavailable"**
The device must be online and the Sunnylink API must be reachable. Check your comma device's connectivity. Entities will recover automatically on the next poll.

**A setting doesn't change on the device**
Some settings only take effect when the device is in offroad mode, or require a reboot. This is a sunnypilot constraint, not an integration issue.

---

## Sharing blurb

I put together an unofficial Home Assistant custom integration for sunnypilot / SunnyLink.

Repo: https://github.com/EarlCrane/sunnypilot_haos

This is my first integration. I had the idea on a Friday, worked through it over the weekend, and was surprised by how quickly Home Assistant, HACS, and SunnyLink could be wired together.

What it does:
- Exposes 67 sunnypilot parameters as native Home Assistant entities
- Adds 49 switches, 17 number controls, and 1 select control
- Supports settings like Experimental Mode, MADS, openpilot Enabled, SSH, Driving Personality, torque tuning, upload controls, and more
- Polls SunnyLink for current state and refreshes state after writes
- Includes a Lovelace dashboard YAML
- Installs through HACS as a custom repository

Current status:
- Working on my comma 4 / sunnypilot setup
- Early community-maintained project
- Uses SunnyLink cloud polling, so it depends on SunnyLink auth/API behavior
- Not affiliated with or maintained by sunnypilot, comma, or Home Assistant

Known limitations:
- Some settings can affect driving behavior; use with care
- Some settings may only apply offroad or after a device reboot
- Voice control through Nabu Casa / Alexa is planned, but only expose controls you are comfortable triggering by voice

Issues and PRs are welcome on GitHub.

---

## Credits

- [sunnypilot](https://github.com/sunnyhaibin/sunnypilot) by sunnyhaibin
- [Sunnylink](https://www.sunnylink.ai) — the cloud backend this integration talks to
- Built for personal use; not affiliated with the sunnypilot project
