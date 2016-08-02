import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO, fileIO
from collections import namedtuple, defaultdict
from datetime import datetime
from random import randint
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import json
import os
import time
import logging
import sys
import threading
from inspect import isclass as _isclass

class Achievement(object):
    """
    Base Achievement class.
    An achievement primarily consists of 'goals', being levels that can be reached. Instances of
    Achievements are used to track progress, and the current level for individual IDs. For this,
    an Achievement implements a number of functions to interact with the current level.
    Achievements can also have a ``category`` (string) and ``keywords`` (tuple of strings) that can
    be used to filter Achievements.
    Goals are defined as a tuple of tuples with the format:
    .. code-block:: python
        goals = (
            {'level': 10, 'name': 'Level 1', 'icon': icons.star, 'description': 'Level One'},
            {'level': 20, 'name': 'Level 2', 'icon': icons.star, 'description': 'Level Two'},
            {'level': 30, 'name': 'Level 3', 'icon': icons.star, 'description': 'Level Three'},
        )
    Arguments:
        level
            A positive integer that must be reached (greater than or equal) to be considered 'met'
        name
            A short name for the level
        icon
            The ``Icon`` to represent the level before it has been achieved. This must be an
            :py:mod:`pychievements.icons.Icon` class.
        .. note::
            There are simple ASCII icons available from :py:mod:`pychievements.icons`
        description
            A longer description of the level.
    Achievements can be updated in two ways: ``increment`` and ``evaluate``. Increment increments
    the current level given an optional set of arguments, where evaluate performs a custom
    evaluation a sets the current level based on that evaluation.
    Increment is best used when the application is aware of achievement tracking, and calls
    to increment can be placed throughout the application.
    Evaluate is best used when actions may happen externally, and cannot be tracked using repeated
    calls to increment. Evaluate will also return the list of achieved goals after it has performed
    its evaluation.
    An Achievement can be initialized with a ``current`` level, for example when restoring for a
    saved state.
    """
    name = 'Achievement'
    category = 'achievements'
    keywords = tuple()
    goals = tuple()

    def __init__(self, current=0):
        self._current = current
        self.goals = sorted(self.goals, key=lambda g: g['level'])  # make sure our goals are sorted

    def __repr__(self):
        to_save = {}
        for key_server, value_server in self.accounts.items():
            to_save[key_server] = {}
            for key_user, value_user in value_server.items():
                to_save[key_server][key_user] = {}
                for key_achievement, value_achievement in value_user.items():
                    to_save[key_server][key_user][key_achievement.__name__] = key_achievement._current
        return json.dumps(to_save)

    @property
    def current(self):
        """
        Returns the current level being achieved (meaning haven't achieved yet) as a tuple:
        ::
            (current_level, (required_level, name, icon, description))
        If all achievements have been achieved, the current level is returned with a None:
        ::
            (current_level, None)
        """
        g = [_ for _ in self.goals if self._current < _['level']]
        if g:
            return (self._current, g[0])
        return (self._current, None)

    @property
    def current_name(self):
        """
        Returns the current level being achieved (meaning haven't achieved yet) as a tuple:
        ::
            (current_level, (required_level, name, icon, description))
        If all achievements have been achieved, the current level is returned with a None:
        ::
            (current_level, None)
        """
        g = [_ for _ in self.goals if self._current < _['level']]
        if g:
            return g[0]['name']
        return None

    @property
    def current_description(self):
        """
        Returns the current level being achieved (meaning haven't achieved yet) as a tuple:
        ::
            (current_level, (required_level, name, icon, description))
        If all achievements have been achieved, the current level is returned with a None:
        ::
            (current_level, None)
        """
        g = [_ for _ in self.goals if self._current < _['level']]
        if g:
            return g[0]['description']
        return None

    @property
    def achieved(self):
        """
        Returns a list of achieved goals
        """
        return [_ for _ in self.goals if self._current >= _['level']]

    @property
    def unachieved(self):
        """
        Returns a list of goals that have not been met yet
        """
        return [_ for _ in self.goals if self._current < _['level']]

    def add_goal(self, level, name, description):
        result = list(self.goals)
        result.append({'level': level, 'name': name, 'description': description})
        self.goals = sorted(tuple(result), key=lambda g: g['level'])  # make sure our goals are sorted
        #TODO maybe good?

    def remove_goal(self, name, level):
        result = list(self.goals)
        result = [_ for _ in result if not (_.get('name') == name or _.get('level') == level)]
        self.goals = sorted(tuple(result), key=lambda g: g['level'])  # make sure our goals are sorted
        #TODO maybe good?

    def increment(self, amount=1, *args, **kwargs):
        """
        Increases the current level. Achievements can redefine this function to take options to
        increase the level based on given arguments. By default, this will simply increment the
        current count by ``amount`` (which defaults to 1).
        """
        self._current = self._current + amount

    def evaluate(self, *args, **kwargs):
        """
        Performs a custom evaluation to set the current level of an achievement. Returns a list of
        achieved goals after the level is determined.
        """
        return self.achieved

    def set_level(self, level):
        """
        Overrides the current level with the given level
        """
        self._current = level

def _make_id(target):
    if hasattr(target, '__func__'):
        return (id(target.__self__), id(target.__func__))
    return id(target)

NONE_ID = _make_id(None)


class Signal(object):
    """
    Base class for all signals
    Internal attributes:
        receivers
            { receiverkey(id): receiver }
    """
    def __init__(self):
        self.receivers = []
        self.lock = threading.Lock()

    def connect(self, receiver, sender=None, dispatch_uid=None):
        """
        Connect receiver to sender for signal.
        Arguments:
            receiver
                A function or an instance method which is to recieve signals.
            sender
                The sender to which the receiver should respond. Must be None to recieve events
                from any sender.
            dispatch_uid
                An identifier used to uniquely identify a particular instance of a receiver. This
                will usually be a string, though it may be anything hashable.
        """
        if dispatch_uid:
            lookup_key = (dispatch_uid, _make_id(sender))
        else:
            lookup_key = (_make_id(receiver), _make_id(sender))

        with self.lock:
            for r_key, _ in self.receivers:
                if r_key == lookup_key:
                    break
            else:
                self.receivers.append((lookup_key, receiver))

    def disconnect(self, receiver=None, sender=None, dispatch_uid=None):
        """
        Disconnect receiver from sender for signal.
        Arguments:
            receiver
                The registered receiver to disconnect. May be none if
                dispatch_uid is specified.
            sender
                The registered sender to disconnect
            dispatch_uid
                the unique identifier of the receiver to disconnect
        """
        if dispatch_uid:
            lookup_key = (dispatch_uid, _make_id(sender))
        else:
            lookup_key = (_make_id(receiver), _make_id(sender))

        with self.lock:
            for index in range(len(self.receivers)):
                (r_key, _) = self.receivers[index]
                if r_key == lookup_key:
                    del self.receivers[index]
                    break

    def has_listeners(self, sender=None):
        return bool(self._receivers(sender))

    def send(self, sender, **named):
        """
        Send signal from sender to all connected receivers.
        If any receiver raises an error, the error propagates back through send,
        terminating the dispatch loop, so it is quite possible to not have all
        receivers called if a raises an error.
        Arguments:
            sender
                The sender of the signal Either a specific object or None.
            named
                Named arguments which will be passed to receivers.
        Returns a list of tuple pairs [(receiver, response), ... ].
        """
        responses = []
        for receiver in self._receivers(sender):
            response = receiver(signal=self, sender=sender, **named)
            responses.append((receiver, response))
        return responses

    def send_robust(self, sender, **named):
        """
        Send signal from sender to all connected receivers catching errors.
        Arguments:
            sender
                The sender of the signal. Can be any python object (normally one
                registered with a connect if you actually want something to
                occur).
            named
                Named arguments which will be passed to receivers. These
                arguments must be a subset of the argument names defined in
                providing_args.
        Return a list of tuple pairs [(receiver, response), ... ].
        If any receiver raises an error (specifically any subclass of
        Exception), the error instance is returned as the result for that
        receiver. The traceback is always attached to the error at
        ``__traceback__``.
        """
        responses = []

        # Call each receiver with whatever arguments it can accept.
        # Return a list of tuple pairs [(receiver, response), ... ].
        for receiver in self._receivers(sender):
            try:
                response = receiver(signal=self, sender=sender, **named)
            except Exception as err:
                if not hasattr(err, '__traceback__'):
                    err.__traceback__ = sys.exc_info()[2]
                responses.append((receiver, err))
            else:
                responses.append((receiver, response))
        return responses

    def _receivers(self, sender):
        """
        Filter sequence of receivers to get receivers for sender.
        """
        with self.lock:
            senderkey = _make_id(sender)
            receivers = []
            for (_, r_senderkey), receiver in self.receivers:
                if r_senderkey == NONE_ID or r_senderkey == senderkey:
                    receivers.append(receiver)
        return receivers


def receiver(signal, **kwargs):
    """
    A decorator for connecting receivers to signals. Used by passing in the
    signal (or list of signals) and keyword arguments to connect::
        @receiver(goal_achieved)
        def signal_receiver(sender, **kwargs):
            ...
        @receiver([goal_achieved, level_increased], sender=tracker)
        def signals_receiver(sender, **kwargs):
            ...
    """
    def _decorator(func):
        if isinstance(signal, (list, tuple)):
            for s in signal:
                s.connect(func, **kwargs)
        else:
            signal.connect(func, **kwargs)
        return func
    return _decorator


goal_achieved = Signal()
level_increased = Signal()
highest_level_achieved = Signal()

class AchievementBackend(object):
    def __init__(self, file_path):
        self.file_path = file_path
        self.accounts = dataIO.load_json(file_path)

    def achievement_for_id(self, user, achievement):
        """ Retrieves the current ``Achievement`` for the given ``tracked_id``. If the given
        ``tracked_id`` does not exist yet, it should be created. Also, if the given ``tracked_id``
        hasn't tracked the given ``Achievement`` yet, a new instance of the ``Achievement`` should
        be created for the given ``tracked_id``"""
        server = user.server
        if server.id not in self.accounts:
            self.accounts[server.id] = {}
        if user.id not in self.accounts[server.id]:
            self.accounts[server.id][user.id] = {}
        if achievement.__name__ not in self.accounts[server.id][user.id]:
            self.accounts[server.id][user.id][achievement.__name__] = achievement()
        self._save_loyalty();
        return self.accounts[server.id][user.id][achievement.__name__]

    def achievements_for_id(self, user, achievements):
        """
        Returns the current achievement for each achievement in ``achievements`` for the given
        tracked_id """
        r = []
        for a in achievements:
            r.append(self.achievement_for_id(user, a))
        self._save_loyalty();
        return r

    def set_level_for_id(self, user, achievement, level):
        """ Set the ``level`` for an ``Achievement`` for the given ``tracked_id`` """
        server = user.server
        if server.id not in self.accounts:
            self.accounts[server.id] = {}
        if user.id not in self.accounts[server.id]:
            self.accounts[server.id][user.id] = {}
        if achievement.__name__ not in self.accounts[server.id][user.id]:
            self.accounts[server.id][user.id][achievement.__name__] = achievement(current=level)
        self.accounts[server.id][user.id][achievement.__name__].set_level(level)
        self._save_loyalty();

    def get_tracked_ids(self):
        return self.accounts[server.id].keys()

    def remove_id(self, user):
        """ Removes *tracked_id* from the backend """
        if user.id in self.accounts[user.server.id]:
            del self.accounts[server.id][user.id]
        self._save_loyalty();

    def wipe_achievements(self, server):
        self.accounts[server.id] = {}
        self._save_loyalty()

    def _load_loyalty(self, file_path, achievement):
        self.accounts = dataIO.load_json(file_path)
        for key_server, value_server in self.accounts.items():
            self.accounts[key_server] = {}
            for key_user, value_user in value_server.items():
                self.accounts[key_server][key_user] = {}
                for key_achievement, value_achievement in value_user.items():
                    temp = self.accounts[key_server][key_user][key_achievement]._current
                    self.accounts[key_server][key_user][key_achievement] = achievement(current=temp)

    def _save_loyalty(self):
        to_save = {}
        for key_server, value_server in self.accounts.items():
            to_save[key_server] = {}
            for key_user, value_user in value_server.items():
                to_save[key_server][key_user] = {}
                for key_achievement, value_achievement in value_user.items():
                    to_save[key_server][key_user][key_achievement] = key_achievement[0]
        dataIO.save_json(self.file_path, to_save)

class AlreadyRegistered(Exception):
        pass


class NotRegistered(Exception):
    pass


class AchievementTracker(object):
    """
    AchievementTracker tracks achievements and current levels for ``tracked_id`` using a configured
    achievement backend.
    A default instance of Achievement tracker is created as a singleton when pycheivements is
    imported as ``pychievements.tracker``. Most often, this is what you will want to use.
    Arguments:
        backend:
            The backend to use for storing/retrieving achievement data. If ``None``, the default
            :py:class:`AchievementBackend` will be used, which stores all data in memory.
    .. note::
        The backend the tracker is using can be updated at any time using the :py:func:`set_backend`
        function.
    """
    def __init__(self, file_path):
        self._registry = []
        self.backend = AchievementBackend(file_path)

    def register(self, achievement_or_iterable, **options):
        """
        Registers the given achievement(s) to be tracked.
        """
        if _isclass(achievement_or_iterable) and issubclass(achievement_or_iterable, Achievement):
            achievement_or_iterable = [achievement_or_iterable]
        for achievement in achievement_or_iterable:
            if not achievement.category:
                raise ValueError('Achievements must specify a category, could not register '
                                 '%s' % achievement.__name__)
            if achievement in self._registry:
                raise AlreadyRegistered('The achievement %s is already '
                                        'registered' % achievement.__name__)
            if achievement is not Achievement:
                self._registry.append(achievement)

    def unregister(self, achievement_or_iterable):
        """
        Un-registers the given achievement(s).
        If an achievement isn't already registered, this will raise NotRegistered.
        """
        if _isclass(achievement_or_iterable) and issubclass(achievement_or_iterable, Achievement):
            achievement_or_iterable = [achievement_or_iterable]
        for achievement in achievement_or_iterable:
            if achievement not in self._registry:
                raise NotRegistered('The achievement %s is not registered' % achievement.__name__)
            self._registry.remove(achievement)

    def is_registered(self, achievement):
        """
        Check if an achievement is registered with this `AchievementTracker`
        """
        return achievement in self._registry

    def achievements(self, category=None, keywords=[]):
        """
        Returns all registered achievements.
        Arguments:
            category
                Filters returned achievements by category. This is a strict string match.
            keywords
                Filters returned achievements by keywords. Returned achievements will match all
                given keywords
        """
        achievements = []
        for achievement in self._registry:
            if category is None or achievement.category == category:
                if not keywords or all([_ in achievement.keywords for _ in keywords]):
                    achievements.append(achievement)
        return achievements

    def achievement_for_id(self, user, achievement):
        """
        Returns ``Achievement`` for a given ``tracked_id``. Achievement can be an ``Achievement``
        class or a string of the name of an achievement class that has been registered with this
        tracker.
        Raises NotRegistered if the given achievement is not registered with the tracker.
        If ``tracked_id`` has not been tracked yet by this tracker, it will be created.
        """
        if isinstance(achievement, Achievement):
            achievement = achievement.__class__.__name__
        elif _isclass(achievement) and issubclass(achievement, Achievement):
            achievement = achievement.__name__

        a = [_ for _ in self._registry if _.__name__ == achievement]
        if a:
            return self.backend.achievement_for_id(user, a[0])
        raise NotRegistered('The achievement %s is not registered with this tracker' % achievement)

    def achievements_for_id(self, user, category=None, keywords=[]):
        """ Returns all of the achievements for tracked_id that match the given category and
        keywords """
        return self.backend.achievements_for_id(user, self.achievements(category, keywords))

    def _check_signals(self, tracked_id, achievement, old_level, old_achieved):
        cur_level = achievement.current[0]
        if old_level < cur_level:
            level_increased.send_robust(self, tracked_id=tracked_id, achievement=achievement)
        if old_achieved != achievement.achieved:
            new_goals = [_ for _ in achievement.achieved if _ not in old_achieved]
            goal_achieved.send_robust(self, tracked_id=tracked_id, achievement=achievement,
                                      goals=new_goals)
            if not achievement.unachieved:
                highest_level_achieved.send_robust(self, tracked_id=tracked_id,
                                                   achievement=achievement)
            return new_goals
        return False

    def increment(self, user, achievement, amount=1, *args, **kwargs):
        """
        Increments an achievement for a given ``tracked_id``. Achievement can be an ``Achievement``
        class or a string of the name of an achievement class that has been registered with this
        tracker.
        Raises NotRegistered if the given achievement is not registered with the tracker.
        If ``tracked_id`` has not been tracked yet by this tracker, it will be created before
        incrementing.
        Returns an list of achieved goals if a new goal was reached, or False
        """
        achievement = self.achievement_for_id(user, achievement)
        cur_level = achievement.current[0]
        achieved = achievement.achieved[:]
        achievement.increment(amount, *args, **kwargs)
        self.backend.set_level_for_id(user, achievement.__class__, achievement.current[0])
        return self._check_signals(user.id, achievement, cur_level, achieved)

    def evaluate(self, user, achievement, *args, **kwargs):
        """
        Evaluates an achievement for a given ``tracked_id``. Achievement can be an ``Achievement``
        class or a string of the name of an achievement class that has been registered with
        this tracker.
        Raises NotRegistered if the given achievement is not registered with the tracker.
        If ``tracked_id`` has not been tracked yet by this tracker, it will be created before
        evaluating.
        Returns list of achieved goals for the given achievement after evaluation
        """
        achievement = self.achievement_for_id(user, achievement)
        cur_level = achievement.current[0]
        achieved = achievement.achieved[:]
        result = achievement.evaluate(*args, **kwargs)
        self.backend.set_level_for_id(user, achievement.__class__, achievement.current[0])
        self._check_signals(user.id, achievement, cur_level, achieved)
        return result

    def current(self, user, achievement):
        """
        Returns ``current`` for a given tracked_id. See :ref:``Achievement``
        """
        achievement = self.achievement_for_id(user, achievement)
        return achievement.current

    def current_name(self, user, achievement):
        """
        Returns ``current`` for a given tracked_id. See :ref:``Achievement``
        """
        achievement = self.achievement_for_id(user, achievement)
        return achievement.current_name

    def current_description(self, user, achievement):
        """
        Returns ``current`` for a given tracked_id. See :ref:``Achievement``
        """
        achievement = self.achievement_for_id(user, achievement)
        return achievement.current_description

    def achieved(self, user, achievement):
        """
        Returns ``achieved`` for a given tracked_id. See :ref:``Achievement``
        """
        achievement = self.achievement_for_id(user, achievement)
        return achievement.achieved

    def unachieved(self, user, achievement):
        """
        Returns ``unachieved`` for a given tracked_id. See :ref:``Achievement``
        """
        achievement = self.achievement_for_id(user, achievement)
        return achievement.unachieved

    def set_level(self, user, achievement, level):
        """
        Returns ``set_level`` for a given tracked_id. See :ref:``Achievement``
        """
        achievement = self.achievement_for_id(user, achievement)
        cur_level = achievement.current[0]
        achieved = achievement.achieved[:]
        achievement.set_level(level)
        self.backend.set_level_for_id(user, achievement.__class__, achievement.current[0])
        self._check_signals(user.id, achievement, cur_level, achieved)

    def get_tracked_ids(self):
        """ Returns all tracked ids """
        return self.backend.get_tracked_ids()

    def remove_id(self, user):
        """ Remove all tracked information for tracked_id """
        self.backend.remove_id(user)

    def add_goal(self, achievement, level, name, description):
        achievement.add_goal(level, name, description)

    def remove_goal(self, achievement, name, level):
        achievement.remove_goal(name, level)


class DiscordAchievement(Achievement):
    """
    Achievements can have as many goals as they like
    """
    name = 'Chat Loyalty'
    category = 'chat'
    saved_goals = dataIO.load_json("data/loyalty/settings.json")
    goals = tuple()
    if saved_goals:
        goals = sorted(saved_goals['goals'], key=lambda g: g['level'])
    else:
        goals = (
            {'level': 1, 'name': 'My First Creation', 'description': 'and it\'s so beautiful....'},
            {'level': 100, 'name': 'Green thumb', 'description': 'You\'ve created at least 5 objects!'},
            {'level': 1000, 'name': 'Clever thinker', 'description': 'More than 10 new creations are all because of you.'},
            {'level': 10000, 'name': 'Almost an adult', 'description': 'Just about 18.'},
            {'level': 100000, 'name': 'True Inspiration', 'description': 'Or did you steal your ideas for these 15 items? Hmm?'},
            {'level': 200000, 'name': 'Divine Creator', 'description': 'All the world bows to your divine inspiration.'},
        )

    def evaluate(self, good_points, bad_points, *args, **kwargs):
        self._current += good_points
        self._current -= bad_points
        return self.achieved

class Loyalty:
    def __init__(self, bot, file_path):
        self.tracker = AchievementTracker("data/loyalty/loyalty.json")
        self.tracker.register(DiscordAchievement)
        self.bot = bot

    @commands.group(name="loyalty", pass_context=True)
    async def _loyalty(self, ctx):
        """Loyalty operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_loyalty.command(pass_context=True, no_pm=True)
    async def buylevel(self, ctx, points : int):
        """Buy loyalty with economy points!"""
        user = ctx.message.author
        good_points = points
        bad_points = 0
        bank = ctx.bot.get_cog("Economy").bank
        if bank.can_spend(user, points):
            self.tracker.evaluate(user, DiscordAchievement, good_points, bad_points)
            bank.withdraw_credits(user, points)
            self.backend._save_loyalty();
            goals = self.tracker.achieved(user, DiscordAchievement)
            if len(goals) > 0:
                goal = goals[-1]
            else:
                goal = {'level': 0, 'name':'idk', 'description':'git gud scrub'}
            points = goal['name']
            level = goal['level']
            desc = goal['description']
            await self.bot.say("{0} You have {1} points!\n You are: {2} -{3}".format(user.mention, points, level, desc))
        else:
            await self.bot.say("You don't have that many points!")

    @_loyalty.command(pass_context=True)
    async def getlevel(self, ctx):
        """Get current loyalty level and associated rank"""
        user = ctx.message.author
        goals = self.tracker.achieved(user, DiscordAchievement)
        if len(goals) > 0:
            goal = goals[-1]
        else:
            goal = {'level': 0, 'name':'idk', 'description':'git gud scrub'}
        points = goal['name']
        level = goal['level']
        desc = goal['description']
        await self.bot.say("{0} You have {1} points!\n You are: {2} -{3}".format(user.mention, points, level, desc))

    @_loyalty.command()
    @checks.admin_or_permissions(manage_server=True)
    async def addgoal(self, level : int, name : str, *description : str):
        """adds a goal to chat goals"""
        actual_name = name
        desc = " ".join(description)
        self.tracker.add_goal(DiscordAchievement, level, actual_name, desc)
        to_save = {}
        to_save['goals'] = DiscordAchievement.goals
        dataIO.save_json("data/loyalty/settings.json", to_save)

    @_loyalty.command()
    @checks.admin_or_permissions(manage_server=True)
    async def removegoal(self, level : int, *name : str):
        """removes a goal from chat goals"""
        actual_name = " ".join(name)
        self.tracker.remove_goal(DiscordAchievement, level, actual_name)
        to_save = {}
        to_save['goals'] = DiscordAchievement.goals
        dataIO.save_json("data/loyalty/settings.json", to_save)

def check_folders():
    if not os.path.exists("data/loyalty"):
        print("Creating data/loyalty folder...")
        os.makedirs("data/loyalty")

def check_files():
    f = "data/loyalty/settings.json"
    if not fileIO(f, "check"):
        print("Creating default loyalty settings.json...")
        fileIO(f, "save", {})

    f = "data/loyalty/loyalty.json"
    if not fileIO(f, "check"):
        print("Creating empty loyalty.json...")
        fileIO(f, "save", {})

def setup(bot):
    global logger
    check_folders()
    check_files()
    bot.add_cog(Loyalty(bot, "data/loyalty/loyalty.json"))
