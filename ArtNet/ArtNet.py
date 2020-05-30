# TODO LIST: Config Wizard, Turn off lights trigger (Artnet muss alle values auf 0 stellen), recognize termination

"""
Author: Lasse Götte
Date: 28.05.2020
Python Version: Python 3.6.9
Source: <Github-Link>
"""
import lightpack, StupidArtnet, configparser, os, re, sys
from time import sleep
from itertools import combinations
from bs4 import BeautifulSoup

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ArtNet:
    def __init__(self):
        base = os.path.dirname(os.path.abspath(__file__))
        html = open(os.path.join(base, 'site/log.html'))
        self.log = BeautifulSoup(html, 'html.parser')
        self.log.find(id='log').clear()
        with open("site/log.html", "wb") as fp:
            fp.write(self.log.prettify("utf-8"))

        self._load_config()
        self._connect_to_lightpack()
        self._load_fixtures()
        self._connect_to_artnet()

    # Load INI file
    def _load_config(self):
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.config = configparser.ConfigParser()
        self.config.read(self.script_dir + '/ArtNet.ini')
        self.fps = self.config.getint('Settings', 'FPS')

    # Setup Fixtures
    def _load_fixtures(self):
        self.fixtures = []
        fixture_objs = []
        for fixture in self.config.sections():
            if fixture.startswith('Fixture_'):

                channel_range = self.config.get(fixture, 'range').rsplit(',')
                mapping = self.config.get(fixture, 'mapping')

                # Start of errorhandling
                if int(channel_range[0]) * int(channel_range[1]) < 1:
                    self._report_error('ERROR-01: ' + fixture + 's start channel or channel count is 0')
                if int(channel_range[0]) < 1 or int(channel_range[0])+int(channel_range[1])-1 > 512:
                    self._report_error('ERROR-02: ' + fixture + 's channelrange has to be in 1-512')
                if not self._match_regex(r"^[RGBD-]*$", mapping):
                    self._report_error('ERROR-03: Illegal character(s) in ' + fixture + 's Mapping')
                if (mapping.count('R') > 1 or mapping.count('G') > 1 or mapping.count('B') > 1 or mapping.count('D') > 1):
                    self._report_error('ERROR-04: R/G/B/D is more than once in ' + fixture + 's Mapping')
                if (mapping.count('R') < 1 or mapping.count('G') < 1 or mapping.count('B') < 1 or mapping.count('D') < 1):
                    self._report_error('ERROR-05: R/G/B/D is not in ' + fixture + 's Mapping')
                if int(channel_range[1]) != len(mapping):
                    self._report_error('ERROR-06: ' + fixture + 's channel count does not match mapping')
                fixture_objs.append([fixture, int(channel_range[0]), int(channel_range[0])+int(channel_range[1])-1])
                # End of errorhandling

                range_map = list(set(range(int(channel_range[0])-1, int(channel_range[0])+int(channel_range[1])-1)))
                self.fixtures.append(dict(id=len(self.fixtures), name=fixture, r=range_map[mapping.find('R')],
                                          g=range_map[mapping.find('G')], b=range_map[mapping.find('B')],
                                          d=range_map[mapping.find('D')]))

        # Errorhandling 2
        for fixture_tuple in list(combinations(fixture_objs, 2)):
            overlap = set(range(fixture_tuple[0][1], fixture_tuple[0][2] + 1)).intersection(
                range(fixture_tuple[1][1], fixture_tuple[1][2] + 1))
            if len(overlap) > 0:
                self._report_error('WARNING: Channelranges of ' + fixture_tuple[0][0] + ' and ' + fixture_tuple[1][0] + ' are overlapping', True)

        led_count = self.lp.getCountLeds()
        if len(fixture_objs) != led_count:
            self._report_error('ERROR-07: Fixture count does not match Prismatiks LED count (' + str(len(fixture_objs)) + ' Fixtures, ' + str(led_count) + ' LEDS)')

    # Connect to Lightpack API
    def _connect_to_lightpack(self):
        try:
            lightpack_host = self.config.get('Lightpack', 'host')
            lightpack_port = self.config.getint('Lightpack', 'port')
            lightpack_api_key = self.config.get('Lightpack', 'key')
            self.lp = lightpack.lightpack(lightpack_host, lightpack_port, None, lightpack_api_key)
            if self.lp.connect() == -1:
                self._report_error('Lightpack API server is missing')
        except lightpack.CannotConnectError as e:
            self._report_error(e)

    # Connect to Artnet Node
    def _connect_to_artnet(self):
        artnet_host = self.config.get('Artnet', 'host')
        artnet_port = self.config.getint('Artnet', 'port')
        artnet_universe = self.config.getint('Artnet', 'universe')
        self.an = StupidArtnet.StupidArtnet(artnet_host, artnet_port, artnet_universe)

        # Write StupidArtNet Info to html log
        for line in str(self.an).split("\n"):
            self.log.find(id='log').append(BeautifulSoup('<p>' + line + '</p>', 'html.parser'))
        with open("site/log.html", "wb") as fp:
            fp.write(self.log.prettify("utf-8"))
        print(self.an)

    def _match_regex(self,regex,str):
        matches = re.finditer(regex, str, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            return True

    def _report_error(self,msg,warning = False):
        if warning == True:
            print(f"{bcolors.WARNING}" + repr(msg) + f"{bcolors.ENDC}")
            # Write to html log
            self.log.find(id='log').append(BeautifulSoup('<p><span style="color:yellow">'+msg+'</span></p>', 'html.parser'))
            with open("site/log.html", "wb") as fp:
                fp.write(self.log.prettify("utf-8"))
        else:
            print(f"{bcolors.FAIL}" + repr(msg) + f"{bcolors.ENDC}")
            # Write to html log
            self.log.find(id='log').append(BeautifulSoup('<p><span style="color:red">' + msg + '</span></p>', 'html.parser'))
            with open("site/log.html", "wb") as fp:
                fp.write(self.log.prettify("utf-8"))
            sys.exit(1)


    def run(self):
        self.an.start()
        while(True):
            packet_size = self.an.PACKET_SIZE
            packet = bytearray(packet_size)

            colors = self.lp.getColors()
            for fixture in self.fixtures:
                color = colors[fixture['id']].split('-')[1].split(',')
                packet[fixture['r']] = int(color[0])
                packet[fixture['g']] = int(color[1])
                packet[fixture['b']] = int(color[2])
                packet[fixture['d']] = 255

            self.an.set(packet)
            sleep(1 / self.fps)

artnet = ArtNet()
artnet.run()
