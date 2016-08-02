import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO, fileIO
from collections import namedtuple, defaultdict
from datetime import datetime
from random import randint, random
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import asyncio
import os
import time
import logging

default_stocks = {'NNTDO': {'price':100, 'bought':0, 'sold':0},
                  'NASLAQ':{'price':100, 'bought':0, 'sold':0},
                  'SNRLX': {'price':100, 'bought':0, 'sold':0},
                  'WTCHR': {'price':100, 'bought':0, 'sold':0},
                  'DSCRD': {'price':100, 'bought':0, 'sold':0},
                  'PYTHN': {'price':100, 'bought':0, 'sold':0},
                  'CRBDBX':{'price':100, 'bought':0, 'sold':0},
                  'SNY':   {'price':100, 'bought':0, 'sold':0},
                  'CSHMNY':{'price':100, 'bought':0, 'sold':0},
                  'MCRSFT':{'price':100, 'bought':0, 'sold':0},
                  'SNK':   {'price':100, 'bought':0, 'sold':0},
                  'DRG':   {'price':100, 'bought':0, 'sold':0},
                  'GRMN':  {'price':100, 'bought':0, 'sold':0}}

class Stocks:
    def __init__(self, bot):
        self.stocks = dataIO.load_json('data/stocks/stocks.json')
        if not self.stocks:
            self.stocks = default_stocks
        self.portfolios = dataIO.load_json('data/stocks/portfolios.json')
        self.bot = bot

    @commands.group(name="stocks", pass_context=True)
    async def _stocks(self, ctx):
        """Stock operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_stocks.command(pass_context=True, no_pm=True)
    async def buy(self, ctx, stock_name, amount : int):
        """Buy *amount* shares of *stock_name* stock"""
        user = ctx.message.author
        economy = self.bot.get_cog("Economy")
        if economy is not None:
            bank = economy.bank
            if user.id not in self.portfolios:
                self.portfolios[user.id] = {}
            if stock_name in self.stocks:
                if amount > 0:
                    cost = self.stocks[stock_name]['price'] * amount
                    if bank.can_spend(user, cost):
                        bank.withdraw_credits(user, cost)
                        if stock_name in self.portfolios[user.id]:
                            self.portfolios[user.id][stock_name] += amount
                        else:
                            self.portfolios[user.id][stock_name] = amount
                        self.stocks[stock_name]['bought'] += amount
                        dataIO.save_json('data/stocks/portfolios.json', self.portfolios)
                        dataIO.save_json('data/stocks/stocks.json', self.stocks)
                        await self.bot.say("You bought {1} stocks of {0}".format(stock_name, amount))
                    else:
                        await self.bot.say("You don't have enough bank credits to purchase {0} of {1}".format(amount, stock_name))
                else:
                    await self.bot.say("You know better than to try to trick me")
            else:
                await self.bot.say("{0} isn't a valid stock".format(stock_name))
        else:
            await self.bot.say("Couldn't find the Economy cog, please load it before trying to use Stocks")


    @_stocks.command(pass_context=True, no_pm=True)
    async def sell(self, ctx, stock_name, amount : int):
        """Sell *amount* shares of *stock_name* stock"""
        user = ctx.message.author
        economy = self.bot.get_cog("Economy")
        if economy is not None:
            bank = economy.bank
            if user.id not in self.portfolios:
                self.portfolios[user.id] = {}
            if stock_name in self.stocks and stock_name in self.portfolios[user.id]:
                if amount > 0:
                    if self.portfolios[user.id][stock_name] >= amount:
                        price = self.stocks[stock_name]['price'] * amount
                        bank.deposit_credits(user, price)
                        self.portfolios[user.id][stock_name] -= amount
                        self.stocks[stock_name]['sold'] += amount
                        if self.portfolios[user.id][stock_name] == 0:
                            del self.portfolios[user.id][stock_name]
                        dataIO.save_json('data/stocks/portfolios.json', self.portfolios)
                        dataIO.save_json('data/stocks/stocks.json', self.stocks)
                        await self.bot.say("You sold {1} stocks of {0}".format(stock_name, amount))
                    else:
                        await self.bot.say("You don't have enough {0} stocks to sell {1}".format(stock_name, amount))
                else:
                    await self.bot.say("You know better than to try to trick me")
            else:
                await self.bot.say("{0} isn't a valid stock or you don't have any".format(stock_name))
        else:
            await self.bot.say("Couldn't find the Economy cog, please load it before trying to use Stocks")

    @_stocks.command()
    async def listall(self):
        """List stocks and prices"""
        await self.bot.say(self.make_list())

    @_stocks.command(pass_context=True)
    async def portfolio(self, ctx):
        """List stocks and quantities owned"""
        result = "```"
        for key, value in self.portfolios[ctx.message.author.id].items():
            result += "{0} : {1} owned\n".format(key, value)
        result += "```"
        await self.bot.say(result)

    @_stocks.command()
    @checks.admin_or_permissions(manage_server=True)
    async def update(self):
        """Force update stock prices"""
        await self.update_stock_prices()
        sentence = self.make_list()
        self.bot.say(sentence)

    def make_list(self):
        result = "```"
        for key, value in self.stocks.items():
            result += "{0}: {1} points\n".format(key, value['price'])
        result += "```"
        return result

    async def update_stock_prices(self):
        for key, value in self.stocks.items():
            self.stocks[key]['price'] = self.new_price(self.stocks[key])
            self.stocks[key]['bought'] = 0
            self.stocks[key]['sold'] = 0
        dataIO.save_json('data/stocks/stocks.json', self.stocks)

    def new_price(self, stock):
        bought = float(stock['bought'])
        sold = float(stock['sold'])
        total = float(stock['bought'] + stock['sold'])
        rnum =  random()
        if total == 0:
            total = 1
        buy_factor = (bought / total) / 2.0 + 1.0
        sell_factor = 1.0 / ((sold / total) / 2.0 + 1.0)
        random_factor = (rnum / 2.0 + 0.75)
        if rnum < 0.05:
            random_factor = 0.5
        if rnum > 0.95:
            random_factor = 2.0
        result_price = int(float(stock['price']) * random_factor * buy_factor * sell_factor)
        if result_price <= 10:
            result_price = 10
        return result_price

    async def check_update_prices(self):
        await asyncio.sleep(60)
        while "Stocks" in self.bot.cogs:
            if self.bot.user is None:
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(60)
                await self.update_stock_prices()
                await self.bot.say(self.make_list())#maybe this will work...

def check_folders():
    if not os.path.exists("data/stocks"):
        print("Creating data/stocks folder...")
        os.makedirs("data/stocks")

def check_files():
    f = "data/stocks/portfolios.json"
    if not fileIO(f, "check"):
        print("Creating empty portfolios.json...")
        fileIO(f, "save", {})

    f = "data/stocks/stocks.json"
    if not fileIO(f, "check"):
        print("Creating empty stocks.json...")
        fileIO(f, "save", {})

def setup(bot):
    global logger
    check_folders()
    check_files()
    stockmarket = Stocks(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(stockmarket.check_update_prices())
    bot.add_cog(stockmarket)
