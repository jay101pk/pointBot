from sopel import module
from sopel.tools import Identifier

from datetime import datetime

pluginName = "pointBot"

autoMode = False
userList = []
ignoreList = []
botList = []

startHour = 8
stopHour = 17

cmdExpr = r"^([a-zA-Z]+)\b\s?((\w+)\s?(-?\d+)?$|.*)?"
ptExpr = r"^(\+|-)(\d+)\s(?:to\s)?(\w+).*$"
timeExpr = r"^(\d+):(\d+):(\d+)"

def setup(bot):
    # restore()
    pass

@module.interval(300)
def updateGameRunning(bot):
    """
    Update every 5 mins for gamerunning state
    """
    gameRunning = getGameRunning(bot.db, pluginName)
    lastSaveHour = getLastHour(bot.db, pluginName)
    workhour = lastSaveHour >= startHour and lastSaveHour < stopHour
    if gameRunning and not workhour:
        setGameRunning(bot.db, pluginName, False)

    if not gameRunning and workhour:
        setGameRunning(bot.db, pluginName, True)
        resetGame(bot.db, bot.users)
    time = timeExpr.match(str(datetime.now().time()))
    hour = int(time.group(1))
    setLastHour(bot.db, pluginName, hour)

@module.rule(ptExpr)
def addGPoints(bot, trigger):
    """
    Regex that catches increment and decrement of user pts
    """
    if not trigger.is_privmsg:
        gameRunning = getGameRunning(bot.db, trigger.sender)
        if not gameRunning:
            bot.reply("The game is not running right now")
            return
        groups = trigger.groups()
        amount = int(groups[1])
        if len(groups) == 4:
            user = Identifier(groups[3])
        else:
            user = Identifier(groups[2])

        players = getPlayers(bot.db, bot.users)
        buser = players.get(user)
        if buser is None:
            bot.reply("That is not a player")
            return
        gpts = getgpts(bot.db, trigger.nick)
        if gpts is None or abs(amount) > gpts:
            bot.reply("You don't have enough gift points")
            return
        addpts(bot.db, user, amount)

@module.nickname_commands(r'help')
def help(bot, trigger):
    """
    pointBot help command
    """
    print("Admin Commands: start, stop, auto, reset, save, restore, say <msg>, me <action>, msg <nick> <msg>, status <user>, setpts <user/all> <points>, setgp <user/all> <gp>, ignore <user>, unignore <user>")
    bot.say("User Commands: help, rules, points, [e.g. pointBot, help]. PM anything for your status.")
    bot.say("Point Exchanges: +/-<pts> [to] <user> [reason] (e.g. +1 to user for being awesome)")

@module.nickname_commands(r'rules')
def rules(bot, trigger):
    """
    pointBot rules command
    """
    bot.say("Hello, it's me, pointBot. I keep track of +s and -s handed out in the IRC. You get 10 points to give away every day, and these points are refreshed every morning at 8 AM. Using bots is not allowed. If you run into any issues, talk to the admin (JSON). Have a day.")

@module.nickname_commands(r'points')
def displaypoints(bot, trigger):
    """
    prints out the points scoreboard
    """
    players = getPlayers(bot.db, bot.users)
    print(players)
    ptsstring = displayPoints(bot.db, players)
    bot.say(ptsstring)

@module.require_admin()
@module.nickname_commands(r'reset')
def resetcommand(bot, trigger):
    """
    Reset game for the day. Sets all users' gift points to 10
    """
    bot.say('reset')
    players = getPlayers(bot.db, bot.users)
    resetGame(bot.db, players)

@module.require_admin()
@module.nickname_commands(r'setpts')
def setptscommand(bot, trigger):
    """
    Set one user's or all's point count
    """
    args = trigger.group(2).split()
    try:
        args[1] = int(args[1])
    except ValueError:
        bot.reply("Bad number")
        return
    buser = getUserFromUsers(args[0])
    if buser is not None:
        setpts(bot.db, buser.nick, args[1])
    elif args[0].lower() == "all":
        players = getPlayers(bot.db, bot.users)
        for user in players:
            setpts(bot.db, user, args[1])
    else:
        bot.reply("Not a valid user option")

@module.require_admin()
@module.nickname_commands(r'setgpts')
def setgptscommand(bot, trigger):
    """
    Set one user's or all gift point count
    """
    args = trigger.group(2).split()
    try:
        args[1] = int(args[1])
    except ValueError:
        bot.reply("Bad number")
        return
    buser = getUserFromUsers(args[0])
    if buser is not None:
        setgpts(bot.db, buser.nick, args[1])
    elif args[0].lower() == "all":
        players = getPlayers(bot.db, bot.users)
        for user in players:
            setgpts(bot.db, user, args[1])
    else:
        bot.reply("Not a valid user option")

@module.require_admin()
@module.nickname_commands(r'setbot')
def setbotcommand(bot, trigger):
    """
    Set a nick's bot status
    """
    args = trigger.group(2).split()
    if len(args) < 2:
        bot.reply("Wrong usage")
        return
    user = getUserFromUsers(args[0], bot.users)
    isbot = args[1].lower() in ['true', '1', 't', 'y', 'yes']
    if user is not None:
        setUserBotStatus(bot.db, user.nick, isbot)

@module.require_admin()
@module.nickname_commands(r'ignore')
def setignorecommand(bot, trigger):
    """
    Set a nick to ignore status
    """
    args = trigger.group(2).split()
    if len(args) < 1:
        bot.reply("Wrong usage")
        return
    user = getUserFromUsers(args[0], bot.users)
    if user is not None:
        setUserIgnoreStatus(bot.db, user.nick, True)

@module.require_admin()
@module.nickname_commands(r'unignore')
def setunignorecommand(bot, trigger):
    """
    Set a nick to unignore status
    """
    args = trigger.group(2).split()
    if len(args) < 1:
        bot.reply("Wrong usage")
        return
    user = getUserFromUsers(args[0], bot.users)
    if user is not None:
        setUserIgnoreStatus(bot.db, user.nick, False)


"""
DB helper functions
"""
def displayPoints(db, users):
    returnString = "Here is a list of points in the format 'User: Total Points' (* = active)\n"
    # pointlist = getpointList()
    print(users)
    for user in users:
        pts = getpts(db, user)
        returnString += "|{}|: {}, ".format(user, pts)
        print(user, getgpts(db, user))
    return returnString

def resetGame(db, users):
    for user in users:
        db.set_nick_value(user,"gpts", 10)

def getpts(db, user):
    return db.get_nick_value(user, "pts", 0)

def setpts(db, user, pts):
    db.set_nick_value(user, "pts", pts)

def addpts(db, user, pts):
    cpts = getpts(db, user)
    setpts(db, user, pts+cpts)

def getgpts(db, user):
    return db.get_nick_value(user, "gpts", 0)

def setgpts(db, user, gpts):
    db.set_nick_value(user, "gpts", gpts)

def getGameRunning(db, plugin):
    return db.get_plugin_value(plugin, "gamerunning", False)

def setGameRunning(db, plugin, value):
    db.set_plugin_value(plugin, "gamerunning", value)

def getLastHour(db, plugin):
    return db.get_plugin_value(plugin, "lasthour", 0)

def setLastHour(db, plugin, value):
    db.set_plugin_value(plugin, "lasthour", value)

def getUserFromUsers(nick, users):
    return users.get(Identifier(nick))

def getUserBotStatus(db, user):
    return db.get_nick_value(user, "bot", False)

def setUserBotStatus(db, user, status):
    db.set_nick_value(user, "bot", status)

def getUserIgnoreStatus(db, user):
    return db.get_nick_value(user, "ignore", False)

def setUserIgnoreStatus(db, user, status):
    db.set_nick_value(user, "ignore", status)

def getPlayers(db, users):
    players = []
    for user in users:
        print(user, getUserBotStatus(db, user), getUserIgnoreStatus(db, user))
        isplayer =  (getUserBotStatus(db, user) or getUserIgnoreStatus(db, user))
        print(isplayer)
        if isplayer:
            players.append(user)
            print(user)
    return players

