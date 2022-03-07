import asyncio
import os
from datetime import datetime
from pathlib import Path

import simplejson as json
import click
import pyglet
from random import shuffle
import twitter

from api_access import api_user, api_pass, api_server
from content.api import ApiClient
from content.dispatcher import Dispatcher
from content.program import Program, FollowupProgram
from system.config import Config
from system.machine import Machine
from twitter_access import twitter_consumer_key, twitter_consumer_secret, twitter_access_token, twitter_access_token_secret


@click.command()
@click.option('--programs', default='programs.json', help='JSON file with programs')
@click.option('--randomize/--no-random', default=True, help='Randomize order of programs')
@click.option('--followups/--no-followups', default=True, help='Avoid followup programs')
@click.option('--prodmode/--devmode', default=True, help='Mode for development with shorter durations')
class Main(object):
    def __init__(self, programs, randomize, followups, prodmode):
        self._randomize = randomize
        self._followups = followups
        self._config = Config()
        self._config.set_server(api_server)
        self._config.set_dev_mode(not prodmode)
        self._config.set_api_auth((api_user, api_pass))
        self._config.set_meta_data_white_list(['madek_core:authors', 'madek_core:description', 'madek_core:title', 'media_content:title',
                                               'media_content:date_created', 'madek_core:keywords', 'media_set:title',
                                               'institution:institutional_affiliation', 'madek_core:copyright_notice'])
        font_directory = os.path.join(os.path.dirname(__file__), 'fonts')
        self._machine = Machine(font_directory)
        self._api = ApiClient(api_server, api_user, api_pass)
        self._twitter_api = twitter.Api(consumer_key=twitter_consumer_key,
                                        consumer_secret=twitter_consumer_secret,
                                        access_token_key=twitter_access_token,
                                        access_token_secret=twitter_access_token_secret)

        # defining the screens
        screen1 = self._machine.create_screen()
        screen2 = self._machine.create_screen()
        screen3 = self._machine.create_screen()
        self._dispatcher = Dispatcher((screen1, screen2, screen3))

        # log start
        if not os.path.exists(self._config.log_dir):
            os.makedirs(self._config.log_dir)
        self.log_program('*** Start ***')

        # defining programs
        self._programs = []

        # convert relative programs path into an absolute one
        programs = os.path.join(os.path.dirname(__file__), programs)

        with open(programs) as json_data:
            for p in json.load(json_data)['programs']:
                self._programs.append(Program(self._api, p))

        print('{} programs'.format(len(self._programs)))

        if self._randomize:
            shuffle(self._programs)
        self._program_index = -1

        pyglet.clock.schedule_interval(self.on_clock, 1)
        pyglet.app.run()

    def on_clock(self, dt):
        if self._dispatcher.entries_len == 0 and not self._api.session_active:
            self.load_program()

    def load_program(self):
        program = None
        last_program = self._dispatcher.program
        while not program or not program.valid:
            # Decide whether to try a followup program
            if self._followups and last_program and type(last_program) is not FollowupProgram:
                program = FollowupProgram(self._api)
            if program and program.set_reference(last_program):
                print('***** load_program followup {} *****'.format(program._name))
            else:
                self._program_index = (self._program_index + 1) % len(self._programs)
                # shuffle programs?
                middle_index = int(0.5*len(self._programs))
                one_third_index = int(0.3*len(self._programs))
                if self._program_index == 0:
                    # shuffle last two third whenever program loop starts again
                    a = self._programs[:one_third_index]
                    b = self._programs[one_third_index:]
                    shuffle(b)
                    self._programs = a + b
                elif self._program_index == middle_index + 1:
                    # shuffle first half whenever program loop has reached second half
                    a = self._programs[:middle_index]
                    b = self._programs[middle_index:]
                    shuffle(a)
                    self._programs = a + b
                program = self._programs[self._program_index]
            print('***** load_program {} *****'.format(program._name))
            loop = self._api.start_session()
            future = asyncio.ensure_future(program.load(False))
            loop.run_until_complete(future)
            self._api.complete_session()
        if program.valid:
            try:
                self.log_program(program.name)
                self._dispatcher.set_program(program)
                self._dispatcher.start()
                self.tweet_program(program)
            except AssertionError:
                print('Error loading program.')
        else:
            print("---- invalid program ----")

    def log_program(self, name_):
        with open(str(Path(self._config.log_dir,'programs_{}.txt'.format(datetime.now().strftime('%Y-%m-%d')))), 'a') as f:
            f.write('{} {}\n'.format(datetime.now().strftime('%H:%M:%S'),name_))


    def tweet_program(self, program_):
        try:
            if not self._config.dev_mode:
                self._twitter_api.PostUpdate('{} {}{}'.format(program_.name, api_server, program_.web_url))
        except:
            print('Twitter error ...')


if __name__ == '__main__':
    m = Main()
