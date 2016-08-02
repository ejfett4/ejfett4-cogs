import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO, fileIO
from collections import namedtuple, defaultdict
from datetime import datetime
from random import randint
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import re
import os
import time
import logging
import itertools

class Store:
    """Store

    Allows any commands to cost economy.py points
    All commands default to 0 points
    For now it doesn't know about actual available commands, doesn't look at aliases,
        and can register any command including important ones and nonexistant ones
    ^That means you can make the bot do bad things if you aren't careful, be wary
    """
    def __init__(self, bot):
        self.bot = bot
        self.costs = dataIO.load_json('data/store/costs.json')

    def _save_store(self):
        dataIO.save_json("data/store/costs.json", self.costs)

    def getcosts(self):
        return self.costs

    @commands.group(name="store", pass_context=True)
    async def _store(self, ctx):
        """Store operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_store.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def setcost(self, ctx, sum: int, *cmd: str):
        """Set the cost of a command: [prefix]store setcost [command] [cost]"""
        full_cmd = " ".join(cmd)#what is this? lololol...
        if sum > -1:
            self.costs[full_cmd] = sum
            self._save_store()
            await self.bot.say("{0} now costs {1}".format(full_cmd, self.costs[full_cmd]))
        else:
            await self.bot.say("{0} can't be negative".format(sum))

    @_store.command()
    async def getcost(self, *cmd : str):
        """Get the cost of a command: [prefix]store getcost [command]"""
        full_cmd = " ".join(cmd)
        if full_cmd in self.costs:
            await self.bot.say("{0} costs {1}".format(full_cmd, self.costs[full_cmd]))
        else:
            await self.bot.say("{0} is not a command in the store!".format(full_cmd))

def has_moneys(ctx):
    economy = ctx.bot.get_cog("Economy")
    store = ctx.bot.get_cog("Store")
    bank = economy.bank
    message = ctx.message
    author = message.author
    args = ctx.kwargs
    msg = re.split("[" + ctx.prefix + " ]", ctx.message.content)
    cmd = msg[1:3]
    full_cmd = " ".join(cmd)
    print(full_cmd)
    if store is not None:
        if full_cmd in store.getcosts():
            if bank.account_exists(author):
                cost = store.getcosts()[full_cmd]
                if bank.can_spend(author, cost):
                    return True
                else:
                    balance = bank.get_balance(author)
                    ctx.bot.say("{0} You have {1} points, but that costs {2}".format(author.mention, balance, cost))
                    return False
            else:
                ctx.bot.say("{0} You need a bank account to call that command\nYou can get one by typing: {1}bank register".format(author.mention, prefix))
                return False
        else:
            return True
    else:
        return True

async def on_command(command, ctx):
    economy = ctx.bot.get_cog("Economy")
    store = ctx.bot.get_cog("Store")
    author = ctx.message.author
    parent_cmd = command.parent
    args = ctx.kwargs
    msg = re.split("[" + ctx.prefix + " ]", ctx.message.content)
    #indx = len(msg) - len(args)
    #cmd = msg[1:indx]
    cmd = msg[1:3]
    full_cmd = " ".join(cmd)
    print(full_cmd)
    if store is not None:
        if full_cmd in store.getcosts():
            economy.bank.withdraw_credits(author, store.getcosts()[full_cmd])
    pass

def check_folders():
    if not os.path.exists("data/store"):
        print("Creating data/store folder...")
        os.makedirs("data/store")

def check_files():
    f = "data/store/costs.json"
    if not fileIO(f, "check"):
        print("Creating empty costs.json...")
        fileIO(f, "save", {})

def setup(bot):
    global logger
    check_folders()
    check_files()
    bot.add_check(has_moneys)
    bot.add_listener(on_command)
    bot.add_cog(Store(bot))
