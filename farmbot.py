import discord, factorio_rcon, json, os, re, shutil, subprocess, sys, time, urllib.request
from discord import option
from discord.ext import tasks
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

config = json.load(open('config.json'))
intents = discord.Intents.default()
intents.members = True
bot = discord.Bot(intents=intents)

def write_userconfig():
    with open('userconfig.json', 'w') as f:
        json.dump(userconfig, f, indent=2)


def get_factorio_versions():
    FactorioVersionRequest = urllib.request.Request('https://factorio.com/api/latest-releases', headers={'User-Agent' : "Update Check Script v2"})
    FactorioVersions = urllib.request.urlopen(FactorioVersionRequest).read()
    FactorioVersionsObj = json.loads(FactorioVersions)
    FactorioVersionOutput = subprocess.check_output(['/opt/factorio/bin/x64/factorio', '--version'], universal_newlines=True)
    FactorioVersionCurrent = re.search(r'^Version: (\d+\.[0-9.]+) ', FactorioVersionOutput).group(1)
    if (FactorioVersionCurrent != FactorioVersionsObj['stable']['headless']):
        UpdateRequired = True
    else:
        UpdateRequired = False

    VersionInfo = {
        "current": FactorioVersionCurrent,
        "latest_stable": FactorioVersionsObj['stable']['headless'],
        "latest_experimental": FactorioVersionsObj['experimental']['headless'],
        "update_required": UpdateRequired
    }

    return(VersionInfo)


def factorio_version_output(VersionInfo):
    VersionInfoCodeBlock = (
        f"```\n"
        f"Current:             {VersionInfo['current']}\n"
        f"Latest stable:       {VersionInfo['latest_stable']}\n"
        f"Latest experimental: {VersionInfo['latest_experimental']}\n"
        f"```"
    )
    if (VersionInfo['update_required']):
        return(f"Update available:\n{VersionInfoCodeBlock}")
    else:
        return(f"Up to date:\n{VersionInfoCodeBlock}")


def restart_factorio():
    status = subprocess.check_output("sudo systemctl restart factorio".split())
    return(status.decode())


def start_factorio():
    status = subprocess.check_output("sudo systemctl start factorio".split())
    return(status.decode())


def stop_factorio():
    status = subprocess.check_output("sudo systemctl stop factorio".split())
    return(status.decode())


def status_factorio():
    status = subprocess.check_output("systemctl status factorio".split())
    StatusCleanList = []
    for line in status.decode().split('\n'):
        if re.search(r'^\s*CGroup:|--rcon', line):
            break
        StatusCleanList.append(line)
    return('\n'.join(StatusCleanList))


def get_factorio_online_players():
    FactorioClient = factorio_rcon.RCONClient("127.0.0.1", config['rcon_port'], config['rcon_password'])
    PlayersString = FactorioClient.send_command('/players online')
    return(PlayersString)


def get_factorio_online_player_count():
    FactorioClient = factorio_rcon.RCONClient("127.0.0.1", config['rcon_port'], config['rcon_password'])
    PlayerCountString = FactorioClient.send_command('/players online count')
    PlayerCount = int(re.match(r'^Online players \((\d+)\)', PlayerCountString).group(1))
    return(PlayerCount)


def get_factorio_save_names(SavePath):
    Saves = list(SavePath.glob("*.zip"))
    return [ s for s in Saves if SaveFilter.match(s.name) ]


SaveFilter = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_ -]+.zip$')
def get_factorio_current_save():
    SavePath = Path(f"{config['factorio_path']}/saves")
    return SavePath, get_factorio_save_names(SavePath)


def get_factorio_stashes():
    return [ s for s in Path(config['factorio_path']).glob("stash-*") if s.is_dir ]


def convert_filename_to_stash_name(Filename):
    return f"stash-{re.sub(r'.zip$', '', Filename)}"


def convert_filename_to_save_name(Filename):
    return f"{re.sub(r'.zip$', '', Filename)}"


def convert_stash_name_to_filename(StashName):
    return f"{re.sub(r'^stash-', '', StashName)}.zip"


def convert_stash_name_to_save_name(StashName):
    return f"{re.sub(r'^stash-', '', StashName)}"


def convert_save_name_to_stash_name(SaveName):
    return f"stash-{SaveName}"


def create_factorio_stash(NewStashName):
    FactorioPath = Path(config['factorio_path'])
    Stashes = get_factorio_stashes()
    if Stashes and NewStashName in [ s.name for s in Stashes ]:
        raise ValueError('Stash already exists')
    Path.mkdir(f"{FactorioPath}/{NewStashName}", mode=0o775, parents=False, exist_ok=False)
    NewStash = Path(f"{FactorioPath}/{NewStashName}")
    shutil.chown(NewStash, group="factorio")
    return NewStash


def activate_factorio_save(Stash):
    FactorioPath = Path(config['factorio_path'])
    Stashes = get_factorio_stashes()
    CurrentSavePath, CurrentSaveFiles = get_factorio_current_save()
    CurrentSaveStashName = convert_filename_to_stash_name(CurrentSaveFiles[0].name)
    if Stashes and CurrentSaveStashName in [ s.name for s in Stashes ]:
        raise ValueError(f"Stash {CurrentSaveStashName} already exists")
    stop_factorio()
    time.sleep(1)
    CurrentSaveStashPath = Path(f"{FactorioPath}/{CurrentSaveStashName}")
    CurrentSavePath.rename(CurrentSaveStashPath)
    Stash.rename(CurrentSavePath)
    time.sleep(1)
    start_factorio()
    time.sleep(10)


# def get_farmbot_user_permission_level(UserId):
#     return userconfig['users'][UserId]['permission_level']


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await auto_update_check.start()


@bot.slash_command(guild_ids=config['guilds'], description="test command")
async def hello(ctx):
    await ctx.respond("hello")


@bot.slash_command(guild_ids=config['guilds'], description="Start Factorio server")
async def startfactorio(ctx):
    await ctx.respond(start_factorio())


@bot.slash_command(guild_ids=config['guilds'], description="Stop Factorio server")
async def stopfactorio(ctx):
    await ctx.respond(stop_factorio())


@bot.slash_command(guild_ids=config['guilds'], description="Restart Factorio server")
async def restartfactorio(ctx):
    await ctx.respond(restart_factorio())


@bot.slash_command(guild_ids=config['guilds'], description="Show Factorio server status")
async def statusfactorio(ctx):
    await ctx.respond(f"```\n{status_factorio()}\n```")


@bot.slash_command(guild_ids=config['guilds'], description="Check for Factorio updates")
async def checkupdatefactorio(ctx):
    VersionInfo = get_factorio_versions()
    await ctx.respond(factorio_version_output(VersionInfo))


@bot.slash_command(guild_ids=config['guilds'], description="Update Factorio server")
async def updatefactorio(ctx):
    VersionInfo = get_factorio_versions()
    await ctx.respond(factorio_version_output(VersionInfo))
    if VersionInfo['update_required']:
        OnlinePlayerCount = get_factorio_online_player_count()
        if OnlinePlayerCount == 0:
            await ctx.respond(restart_factorio())
            VersionInfo = get_factorio_versions()
            await ctx.respond(factorio_version_output(VersionInfo))
        else:
            await ctx.respond(f"Update aborted, {OnlinePlayerCount} user(s) online")


@bot.slash_command(guild_ids=config['guilds'], description="Enable channel update notifications")
async def enableupdatenotifications(ctx):
    if ctx.channel.id not in userconfig['notification_channels']:
        Channel = bot.get_channel(ctx.channel.id)
        if Channel.can_send:
            userconfig['notification_channels'].append(ctx.channel.id)
            write_userconfig()
            await ctx.respond("Update notifications enabled")
        else:
            await ctx.respond("Cannot send messages to this channel, please fix permissions and try again")
    else:
        await ctx.respond("Update notifications were already enabled, no changes made")


@bot.slash_command(guild_ids=config['guilds'], description="Disable channel update notifications")
async def disableupdatenotifications(ctx):
    if ctx.channel.id in userconfig['notification_channels']:
        if userconfig['automatic_updates'] and len(userconfig['notification_channels']) == 1:
            await ctx.respond("Automatic updates are enabled, and no other channels have notifications enabled. Please disable automatic updates first, or enable notifications on a different channel.")
            return()
        userconfig['notification_channels'].remove(ctx.channel.id)
        write_userconfig()
        await ctx.respond("Update notifications disabled.")
    else:
        await ctx.respond("Update notifications were not enabled, no changes made.")


@bot.slash_command(guild_ids=config['guilds'], description="Enable automatic updates")
async def enableautomaticupdates(ctx):
    if len(userconfig['notification_channels']) == 0:
        await ctx.respond("No update notification channels have been set, please enable update notifications first")
        return()
    if not userconfig['automatic_updates']:
        userconfig['automatic_updates'] = True
        write_userconfig()
        await ctx.respond("Automatic updates enabled")
    else:
        await ctx.respond("Automatic updates were already enabled, no changes made")


@bot.slash_command(guild_ids=config['guilds'], description="Disable automatic updates")
async def disableautomaticupdates(ctx):
    if userconfig['automatic_updates']:
        userconfig['automatic_updates'] = False
        write_userconfig()
        await ctx.respond("Automatic updates disabled")
    else:
        await ctx.respond("Automatic updates were not enabled, no changes made")


@bot.slash_command(guild_ids=config['guilds'], description="Show online players")
async def playersonline(ctx):
    await ctx.respond(f"```\n{get_factorio_online_players()}\n```")


def get_saves_output():
    CurrentSaveName = convert_filename_to_save_name(get_factorio_current_save()[1][0].name)
    StashedSaveNames = [ convert_stash_name_to_save_name(s.name) for s in get_factorio_stashes() ]
    return f"Current Save: `{CurrentSaveName}`\nStashed Saves:\n- `{'`\n- `'.join(StashedSaveNames)}`"


@bot.slash_command(guild_ids=config['guilds'], description="Show saves")
async def showsaves(ctx):
    await ctx.respond(get_saves_output())


@bot.slash_command(guild_ids=config['guilds'], description="Upload save file to new stash")
@option(
    "save_file",
    discord.Attachment,
    description="Save file to import",
    required=True
)
async def uploadnewfactoriosave(ctx, save_file: discord.Attachment):
    if save_file.filename.__len__() > 128:
        ctx.respond(f"Filename is too long, aborting.\nMaximum permitted filename length is 128 characters.")
    if not SaveFilter.match(save_file.filename):
        await ctx.respond(f"Filename uses illegal characters, aborting.\nAllowed Characters are `A-Za-z0-9` for the first character, and `A-Za-z0-9_ -` for subsequent characters.")
    if save_file.filename in [ s.name for s in get_factorio_current_save()[1] ]:
        await ctx.respond(f"Filename in use by current save, aborting.")
        return
    Stashes = get_factorio_stashes()
    NewStashName = convert_filename_to_stash_name(save_file.filename)
    if Stashes and NewStashName in [ s.name for s in Stashes ]:
        await ctx.respond(f"Stash for filename already exists, aborting.")
        return
    NewStash = create_factorio_stash(NewStashName)
    NewSavePath = f"{str(NewStash)}/{save_file.filename}"
    await save_file.save(NewSavePath)
    os.chmod(NewSavePath, 0o664)
    shutil.chown(NewSavePath, group="factorio")
    await ctx.respond(f"File `{save_file.filename}` successfully uploaded to new stash `{NewStashName}`.")


@bot.slash_command(guild_ids=config['guilds'], description="Show your discord user id")
async def showdiscorduserid(ctx):
    await ctx.respond(ctx.author.id)


# @bot.slash_command(guild_ids=config['guilds'], description="Show user debug")
# async def showuserdebug(ctx, user):
#     if not re.match(r'^<@\d+>$', user):
#         await ctx.respond(f"Invalid request, please @tag a user")
#         return
#     UserId = int(re.sub(r'[<>@]', '', user))
#     await ctx.respond([ m.global_name for m in ctx.guild.members if m.id == UserId ])


def clean_tagged_user(User):
    if not re.match(r'^<@\d+>$', User):
        raise ValueError
    return int(re.sub(r'[<>@]', '', User))


def get_discord_user(ctx, UserId):
    Users = [ m for m in ctx.guild.members if m.id == UserId ]
    if len(Users) > 1:
        raise LookupError
    elif len(Users) == 1:
        return Users[0]
    else:
        return None


def get_farmbot_user(UserId: int):
    Users = [ u for u in userconfig['farmbot_users'] if u['id'] == UserId ]
    if len(Users) > 1:
        raise LookupError
    elif len(Users) == 1:
        return Users[0]
    else:
        return None


def get_farmbot_user_index(UserId: int):
    try:
        Index = [ x['id'] for x in userconfig['farmbot_users'] ].index(UserId)
    except ValueError:
        Index = -1
    return Index


async def test_farmbot_user_permission_level(ctx, RequiredPermissionLevel):
    try:
        FbUser = get_farmbot_user(ctx.author.id)
    except LookupError:
        await ctx.respond("Permissions check failed: multiple users found. Aborting."); return
    if FbUser and FbUser['permission_level'] >= RequiredPermissionLevel:
        return True
    else:
        await ctx.respond("Permission denied")
        return False


@bot.slash_command(guild_ids=config['guilds'], description="Create farmbot user")
@option(
    "user",
    str,
    description="@Tagged user to create",
    required=True
)
@option(
    "permission_level",
    int,
    description="Permission level to be given to user, 0-15. 15 is full admin, 0 is banned.",
    min_value=0,
    max_value=15
)
async def createfarmbotuser(ctx, user: str, permission_level: int = 1):
    RequiredPermissionLevel = 15
    if await test_farmbot_user_permission_level(ctx, RequiredPermissionLevel) != True:
        return

    try:
        UserId = clean_tagged_user(user)
    except ValueError:
        await ctx.respond("Invalid request, please @tag a user"); return

    try:
        DiscordUser = get_discord_user(ctx, UserId)
    except LookupError:
        await ctx.respond("Discord user lookup failed: multiple users found. Aborting."); return
    if not DiscordUser:
        await ctx.respond("Discord user not found, aborting."); return

    FbUser = get_farmbot_user(UserId)
    if FbUser:
        await ctx.respond(f"Farmbot user for {FbUser['name']} already exists, aborting."); return

    NewFbUser = {
        'id': UserId,
        'global_name': DiscordUser.global_name,
        'name': DiscordUser.name,
        'permission_level': permission_level
    }
    userconfig['farmbot_users'].append(NewFbUser)
    write_userconfig()
    await ctx.respond(f"Farmbot user created for {user} with permission level {NewFbUser['permission_level']}")


@bot.slash_command(guild_ids=config['guilds'], description="Show farmbot user permission level")
@option(
    "user",
    str,
    description="@Tagged user to create",
    required=True
)
async def showfarmbotuser(ctx, user):
    FbUser = get_farmbot_user(clean_tagged_user(user))
    if FbUser:
        await ctx.respond(f"```json\n{json.dumps(FbUser, indent=2)}\n```")
    else:
        await ctx.respond(f"FarmBot user for {user} not found")


@bot.slash_command(guild_ids=config['guilds'], description="Edit farmbot user permission level")
@option(
    "user",
    str,
    description="@Tagged user to edit",
    required=True
)
@option(
    "permission_level",
    int,
    description="Permission level to be given to user, 0-15. 15 is full admin, 0 is banned.",
    min_value=0,
    max_value=15,
    required=True
)
async def editfarmbotuserpermissionlevel(ctx, user: str, permission_level: int):
    RequiredPermissionLevel = 15
    if await test_farmbot_user_permission_level(ctx, RequiredPermissionLevel) != True:
        return

    try:
        UserId = clean_tagged_user(user)
    except ValueError:
        await ctx.respond("Invalid request, please @tag a user"); return

    try:
        DiscordUser = get_discord_user(ctx, UserId)
    except LookupError:
        await ctx.respond("Discord user lookup failed: multiple users found. Aborting."); return
    if not DiscordUser:
        await ctx.respond("Discord user not found, aborting."); return

    FbUserIndex = get_farmbot_user_index(UserId)
    if FbUserIndex == -1:
        await ctx.respond(f"Farmbot user for {user} does not exist, aborting."); return

    userconfig['farmbot_users'][FbUserIndex]['global_name'] = DiscordUser.global_name
    userconfig['farmbot_users'][FbUserIndex]['name'] = DiscordUser.name
    userconfig['farmbot_users'][FbUserIndex]['permission_level'] = permission_level
    write_userconfig()
    await ctx.respond(f"Farmbot user updated for {user} with permission level {userconfig['farmbot_users'][FbUserIndex]['permission_level']}")


async def removefarmbotuser(ctx, user: str, permission_level: int):
    RequiredPermissionLevel = 15
    if await test_farmbot_user_permission_level(ctx, RequiredPermissionLevel) != True:
        return

    try:
        UserId = clean_tagged_user(user)
    except ValueError:
        await ctx.respond("Invalid request, please @tag a user"); return

    FbUserIndex = get_farmbot_user_index(UserId)
    if FbUserIndex == -1:
        await ctx.respond(f"Farmbot user for {user} does not exist, aborting."); return

    userconfig['farmbot_users'][FbUserIndex].remove()
    write_userconfig()
    await ctx.respond(f"Farmbot user removed for {user}")


async def autocomplete_list_stashes(ctx: discord.AutocompleteContext):
  return [ convert_stash_name_to_save_name(s.name) for s in get_factorio_stashes() ]


@bot.slash_command(guild_ids=config['guilds'], description="Switch Save Files")
@option(
    "save",
    str,
    autocomplete=autocomplete_list_stashes,
    description="Save file to import",
    required=True
)
async def activatefactoriostashedsave(ctx,save: str):
    await ctx.respond(f"Switching to save `{save}`")
    SavePath = Path(f"{config['factorio_path']}/{convert_save_name_to_stash_name(save)}")
    activate_factorio_save(SavePath)
    await ctx.respond(f"Switch Complete.\n```\n{status_factorio()}\n```\n{get_saves_output()}")


async def send_notification(string):
    for Id in userconfig['notification_channels']:
        Channel = bot.get_channel(Id)
        if Channel.can_send:
            await Channel.send(string)
        else:
            print(f"Cannot send update notification to channel {Id} due to permissions")


@tasks.loop(hours=1)
async def auto_update_check():
    VersionInfo = get_factorio_versions()
    if VersionInfo['update_required'] and VersionInfo['latest_stable'] != userconfig['notified_version']:
        userconfig['notified_version'] = VersionInfo['latest_stable']
        write_userconfig()
        await send_notification(factorio_version_output(get_factorio_versions()))
    if VersionInfo['update_required'] and userconfig['automatic_updates']:
        PlayerCount = get_factorio_online_player_count()
        if PlayerCount == 0:
            await send_notification(f"Starting update from version `{VersionInfo['current']}` to version `{VersionInfo['latest_stable']}`, there are 0 players on the server.")
            restart_factorio()
            time.sleep(10)
            await send_notification(f"```\nUpdate complete\n{status_factorio()}\n```")

        elif PlayerCount == 1:
            await send_notification(f"Cannot update from version `{VersionInfo['current']}` to version `{VersionInfo['latest_stable']}`, there is 1 player on the server:\n```\n{get_factorio_online_players()}\n```")
        else: 
            await send_notification(f"Cannot update from version `{VersionInfo['current']}` to version `{VersionInfo['latest_stable']}`, there are `{PlayerCount}` players on the server:\n```\n{get_factorio_online_players()}\n```")


global userconfig

if os.path.isfile('userconfig.json'):
    userconfig = json.load(open('userconfig.json'))
else:
    userconfig = {}

if 'notification_channels' not in userconfig:
    userconfig['notification_channels'] = []
if 'notified_version' not in userconfig:
    userconfig['notified_version'] = ''
if 'automatic_updates' not in userconfig:
    userconfig['automatic_updates'] = False
if 'farmbot_users' not in userconfig:
    userconfig['farmbot_users'] = []
for Admin in config['farmbot_default_admin_discord_users']:
    if not userconfig['farmbot_users'] or Admin['id'] not in [ u['id'] for u in userconfig['farmbot_users'] ]:
        NewFbUser = {
            'id': Admin['id'],
            'global_name': Admin['global_name'],
            'name': Admin['name'],
            'permission_level': 15
        }
        userconfig['farmbot_users'].append(NewFbUser)

write_userconfig()


bot.run(config['token'])
