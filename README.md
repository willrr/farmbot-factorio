# Farmbot-Factorio

Farmbot Factorio is a discord bot for managing a Factorio server. It utilises pycord for discord interaction, factorio_rcon to talk to the factorio process, and the public factorio API for checking version information.

## Features:
- Service management with systemd, including example systemd service files.
- Automatic updating of the code (checks to see if anyone is currently on the server first).
- Executing some in-game commands and returning output to Discord.
- Savegame upload and management (Can stop the server and switch between different savegames).
- A JSON configuration file that can store basic user data, and provide a link between ingame users and discord users.
- A basic permissions system to control who can run which discord command. It supports a range of 0-15, where 0 is no permissions and 15 is full admin.

## Installation:
- Create a linux service user for `factorio`.
- Create a linux service user for `farmbot-factorio`, adding to the `factorio` group (required for updating to work).
- Download and extract factorio to `/opt/factorio`, ensuring that the `factorio` user and group are the owners.
- Download the repository to `/opt/` (so the full path will be `/opt/farmbot-factorio/`), ensuring that the `farmbot-factorio` user and group are the owners.
- Create your python venv (`farmbot-factorio-env` is the recommended name, as this is already part of the `.gitignore` file).
- Install requirements as per `requirements.txt`.
- Use the `config.example.json` file to create `config.json` with your settings. (`/opt/farmbot-factorio/config.json`)
- Use the `factorio.example.service` file to install factorio as a service within systemd (`/etc/systemd/system/factorio.service`). Also remember to set the rcon password to match what is in your `config.json` file.
- Use the `farmbot-factorio.example.service` file to install farmbot-factorio as a service within systemd (`/etc/systemd/system/farmbot-factorio.service`)
- Use the `factorio.sudoers.example` file to allow `farmbot-factorio` service permissions via sudo. (`/etc/sudoers.d/factorio`)
- User the `update.example.py` file to create an `update.py` file. This is executed as part of systemd starting the service.

## Use:
This is not an exhaustive list of all commands, but a few base features:
- Enabling automatic updates:
  - Run `/enableupdatenotifications` in a channel that you want the update notifications to be posted in.
  - Run `/enableautomaticupdates`.
- Uploading and activiating a new save:
  - Run `/uploadnewfactoriosave` and provide the ZIP file.
  - Run `/activatefactoriostashedsave` to load the save. This will stop the server, re-arrange the save files, and start the server again.
- Using the whitelist feature in Factorio:
  - Ask user to run `/registerfarmbotuser` to create themselves a privilege level 1 farmbot user.
  - Ask user to run `/registerfactoriousername` to add their factorio username to their farmbot user, and add it to the ingame whitelist.
- Adjusting a user's permission level
  - Once a user has registered, use `/setfarmbotuserpermissionlevel`

## Possible future features:
- Mod management
- Switching between Factorio update channels (stable / experimental)