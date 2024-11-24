import discord, factorio_rcon, json, os, re, subprocess, sys, time, urllib.request
from discord.ext import tasks

sys.stdout.reconfigure(line_buffering=True)

config = json.load(open('config.json'))
bot = discord.Bot()

def write_userconfig():
    with open('userconfig.json', 'w') as f:
        json.dump(userconfig, f)


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


def status_factorio():
    status = subprocess.check_output("systemctl status factorio".split())
    StatusCleanList = []
    for line in status.decode().split('\n'):
        if re.search(r'^\s*CGroup:|--rcon', line):
            break
        StatusCleanList.append(line)
    return('\n'.join(StatusCleanList))


def get_online_players():
    FactorioClient = factorio_rcon.RCONClient("127.0.0.1", config['rcon_port'], config['rcon_password'])
    PlayersString = FactorioClient.send_command('/players online')
    return(PlayersString)


def get_online_player_count():
    FactorioClient = factorio_rcon.RCONClient("127.0.0.1", config['rcon_port'], config['rcon_password'])
    PlayerCountString = FactorioClient.send_command('/players online count')
    PlayerCount = int(re.match(r'^Online players \((\d+)\)', PlayerCountString).group(1))
    return(PlayerCount)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await auto_update_check()


@bot.slash_command(guild_ids=config['guilds'], description="test command")
async def hello(ctx):
    await ctx.respond("hello")


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
        OnlinePlayerCount = get_online_player_count()
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
    await ctx.respond(f"```\n{get_online_players()}\n```")


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
        send_notification(factorio_version_output(VersionInfo))
    if VersionInfo['update_required'] and userconfig['automatic_updates']:
        PlayerCount = get_online_player_count()
        if PlayerCount == 0:
            send_notification(f"Starting update from version `{VersionInfo['current']}` to version `{VersionInfo['latest_stable']}`, there are 0 players on the server.")
            restart_factorio()
            time.sleep(10)
            send_notification(f"```\n{status_factorio()}\n```")

        elif PlayerCount == 1:
            send_notification(f"Cannot update from version `{VersionInfo['current']}` to version `{VersionInfo['latest_stable']}`, there is 1 player on the server:\n```\n{get_online_players()}\n```")
        else: 
            send_notification(f"Cannot update from version `{VersionInfo['current']}` to version `{VersionInfo['latest_stable']}`, there are `{PlayerCount}` players on the server:\n```\n{get_online_players()}\n```")


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

write_userconfig()


bot.run(config['token'])
