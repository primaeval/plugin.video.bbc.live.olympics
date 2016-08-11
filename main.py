from xbmcswift2 import Plugin
from xbmcswift2 import actions
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import re

import requests
import random

from datetime import datetime,timedelta
import time
#import urllib
import HTMLParser
import xbmcplugin
#import xml.etree.ElementTree as ET
#import sqlite3
import os
#import shutil
#from rpc import RPC
from types import *

plugin = Plugin()
big_list_view = False

def log2(v):
    xbmc.log(repr(v))

def log(v):
    xbmc.log(re.sub(',',',\n',repr(v)))

def get_icon_path(icon_name):
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return os.path.join(addon_path, 'resources', 'img', icon_name+".png")


def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'',label)
    label = re.sub(r"\[/?COLOR.*?\]",'',label)
    return label

def get_tvdb_id(name):
    tvdb_url = "http://thetvdb.com//api/GetSeries.php?seriesname=%s" % name
    try:
        r = requests.get(tvdb_url)
    except:
        return ''
    tvdb_html = r.text
    tvdb_id = ''
    tvdb_match = re.search(r'<seriesid>(.*?)</seriesid>', tvdb_html, flags=(re.DOTALL | re.MULTILINE))
    if tvdb_match:
        tvdb_id = tvdb_match.group(1)
    return tvdb_id


class FileWrapper(object):
    def __init__(self, filename):
        self.vfsfile = xbmcvfs.File(filename)
        self.size = self.vfsfile.size()
        self.bytesRead = 0

    def close(self):
        self.vfsfile.close()

    def read(self, byteCount):
        self.bytesRead += byteCount
        return self.vfsfile.read(byteCount)

    def tell(self):
        return self.bytesRead


@plugin.route('/play_media/<path>/')
def play_media(path):
    cmd = "PlayMedia(%s)" % path
    xbmc.executebuiltin(cmd)



@plugin.route('/device/<channelname>/<device>')
def device(channelname,device):
    items = []

    for cast in ['simulcast', 'webcast']:
        if device in ['abr_hdtv', 'hdtv', 'tv', 'hls_tablet']:
            for provider in ['ak', 'llnw']:
                url = 'http://a.files.bbci.co.uk/media/live/manifesto/audio_video/%s/hls/uk/%s/%s/%s.m3u8' \
                      % (cast, device, provider, channelname)
                r = requests.get(url)
                html = r.content

                for m in re.finditer(r'#EXT-X-STREAM-INF:PROGRAM-ID=(.+?),BANDWIDTH=(.+?),CODECS="(.*?)",RESOLUTION=(.+?)\s*(.+?.m3u8)',html):
                    url = m.group(5)
                    resolution = m.group(4)
                    bitrate = m.group(2)
                    label = "%s m3u8 %s %s %s %s %s" % (channelname, device, cast, provider, bitrate, resolution)
                    items.append({'label':label, 'path':url, 'is_playable':True})

    for cast in ['simulcast', 'webcast']:
        ### HDS  #BUG high bitrate streams play at low bitrate
        if device in ['pc', 'apple-ipad-hls']:
            for provider in ['ak', 'llnw']:
                url = 'http://a.files.bbci.co.uk/media/live/manifesto/audio_video/%s/hds/uk/%s/%s/%s.f4m'  % (cast, device, provider, channelname)
                #print url
                r = requests.get(url)
                html = r.text
                #print html
                streams = re.compile('<media href="(.+?)" bitrate="(.+?)"/>').findall(html)
                #if streams:
                #    print url
                for stream in streams:
                    bitrate = stream[1]
                    #bandwidth = int(int(bitrate) * 1000.0)
                    url = stream[0]
                    url = "plugin://plugin.video.f4mTester/?url=%s" % url
                    label = "%s f4m %s %s %s %s" % (channelname, device, cast, provider, bitrate)
                    items.append({'label':label, 'path':plugin.url_for("play_media",path=url), 'is_playable':False})

    urls = {}
    for protocol in ['hls']:
        if device in ['pc','iptv-all', 'apple-ipad-hls']:
            manifest_url = "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/%s/vpid/%s/transferformat/%s?cb=%d" % \
            (device, channelname, protocol, random.randrange(10000,99999))
            #print manifest_url
            r = requests.get(manifest_url)
            html = r.text
            #print html
            match = re.compile(
                'media.+?bitrate="(.+?)".+?encoding="(.+?)".+?connection.+?href="(.+?)".+?supplier="(.+?)".+?transferFormat="(.+?)"'
                ).findall(html)
            playlist_urls = set()
            for bitrate, encoding, url, supplier, transfer_format in match:
                playlist_urls.add((supplier, url, bitrate))
            for (supplier, playlist_url, bitrate) in playlist_urls:
                r = requests.get(playlist_url)
                html = r.text
                match = re.compile('#EXT-X-STREAM-INF:PROGRAM-ID=(.+?),BANDWIDTH=(.+?),CODECS="(.*?)",RESOLUTION=(.+?)\s*(.+?.m3u8)').findall(html)
                if match:
                    print playlist_url
                for id, bandwidth, codecs, resolution, url in match:
                    urls[url] = (channelname, device, cast, supplier, bandwidth, resolution)

    for url in sorted(urls):
        #xbmc.log(url)
        (channelname, device, cast, supplier, bandwidth, resolution) = urls[url]
        label = "%s m3u8 %s %s %s %s" % (channelname, device, supplier, bandwidth, resolution)
        items.append({'label':label, 'path':url, 'is_playable':True})

    return items


@plugin.route('/channel/<channelname>')
def channel(channelname):
    items = []

    for cast in ['simulcast', 'webcast']:
        for device in ['abr_hdtv', 'hdtv', 'tv', 'hls_tablet']:
            for provider in ['ak', 'llnw']:
                url = 'http://a.files.bbci.co.uk/media/live/manifesto/audio_video/%s/hls/uk/%s/%s/%s.m3u8' \
                      % (cast, device, provider, channelname)
                r = requests.get(url)
                html = r.content

                for m in re.finditer(r'#EXT-X-STREAM-INF:PROGRAM-ID=(.+?),BANDWIDTH=(.+?),CODECS="(.*?)",RESOLUTION=(.+?)\s*(.+?.m3u8)',html):
                    url = m.group(5)
                    resolution = m.group(4)
                    bitrate = m.group(2)
                    label = "%s m3u8 %s %s %s %s %s" % (channelname, device, cast, provider, bitrate, resolution)
                    items.append({'label':label, 'path':url, 'is_playable':True})

    for cast in ['simulcast', 'webcast']:
        ### HDS  #BUG high bitrate streams play at low bitrate
        for device in ['pc', 'apple-ipad-hls']:
            for provider in ['ak', 'llnw']:
                url = 'http://a.files.bbci.co.uk/media/live/manifesto/audio_video/%s/hds/uk/%s/%s/%s.f4m'  % (cast, device, provider, channelname)
                #print url
                r = requests.get(url)
                html = r.text
                #print html
                streams = re.compile('<media href="(.+?)" bitrate="(.+?)"/>').findall(html)
                #if streams:
                #    print url
                for stream in streams:
                    bitrate = stream[1]
                    #bandwidth = int(int(bitrate) * 1000.0)
                    url = stream[0]
                    url = "plugin://plugin.video.f4mTester/?url=%s" % url
                    label = "%s f4m %s %s %s %s" % (channelname, device, cast, provider, bitrate)
                    items.append({'label':label, 'path':plugin.url_for("play_media",path=url), 'is_playable':False})

    urls = {}
    for protocol in ['hls']:
        for device in ['pc','iptv-all', 'apple-ipad-hls']:
            manifest_url = "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/%s/vpid/%s/transferformat/%s?cb=%d" % \
            (device, channelname, protocol, random.randrange(10000,99999))
            #print manifest_url
            r = requests.get(manifest_url)
            html = r.text
            #print html
            match = re.compile(
                'media.+?bitrate="(.+?)".+?encoding="(.+?)".+?connection.+?href="(.+?)".+?supplier="(.+?)".+?transferFormat="(.+?)"'
                ).findall(html)
            playlist_urls = set()
            for bitrate, encoding, url, supplier, transfer_format in match:
                playlist_urls.add((supplier, url, bitrate))
            for (supplier, playlist_url, bitrate) in playlist_urls:
                r = requests.get(playlist_url)
                html = r.text
                match = re.compile('#EXT-X-STREAM-INF:PROGRAM-ID=(.+?),BANDWIDTH=(.+?),CODECS="(.*?)",RESOLUTION=(.+?)\s*(.+?.m3u8)').findall(html)
                if match:
                    print playlist_url
                for id, bandwidth, codecs, resolution, url in match:
                    urls[url] = (channelname, device, cast, supplier, bandwidth, resolution)

    for url in sorted(urls):
        (channelname, device, cast, supplier, bandwidth, resolution) = urls[url]
        label = "%s m3u8 %s %s %s %s" % (channelname, device, supplier, bandwidth, resolution)
        items.append({'label':label, 'path':url, 'is_playable':True})

    return items

@plugin.route('/channels')
def channels():
    items = []
    for channelname in [
        'bbc_one_hd',
        'bbc_two_hd',
        'bbc_four_hd',
        'cbbc_hd',
        'cbeebies_hd',
        'bbc_news24',
        'bbc_parliament',
        'bbc_alba',
        's4cpbs',
        'bbc_one_london',
        'bbc_one_scotland_hd',
        'bbc_one_northern_ireland_hd',
        'bbc_one_wales_hd',
        'bbc_two_england',
        'bbc_two_scotland',
        'bbc_two_northern_ireland_digital',
        'bbc_two_wales_digital',
        'bbc_one_cambridge',
        'bbc_one_channel_islands',
        'bbc_one_east',
        'bbc_one_east_midlands',
        'bbc_one_east_yorkshire',
        'bbc_one_north_east',
        'bbc_one_north_west',
        'bbc_one_oxford',
        'bbc_one_south',
        'bbc_one_south_east',
        'bbc_one_west',
        'bbc_one_west_midlands',
        'bbc_one_yorks',
        'sport_stream_01',
        'sport_stream_02',
        'sport_stream_03',
        'sport_stream_04',
        'sport_stream_05',
        'sport_stream_06',
        'sport_stream_07',
        'sport_stream_08',
        'sport_stream_09',
        'sport_stream_10',
        'sport_stream_11',
        'sport_stream_12',
        'sport_stream_13',
        'sport_stream_14',
        'sport_stream_15',
        'sport_stream_16',
        'sport_stream_17',
        'sport_stream_18',
        'sport_stream_19',
        'sport_stream_20',
        'sport_stream_21',
        'sport_stream_22',
        'sport_stream_23',
        'sport_stream_24',
        'sport_stream_01b',
        'sport_stream_02b',
        'sport_stream_03b',
        'sport_stream_04b',
        'sport_stream_05b',
        'sport_stream_06b',
        'sport_stream_07b',
        'sport_stream_08b',
        'sport_stream_09b',
        'sport_stream_10b',
        'sport_stream_11b',
        'sport_stream_12b',
        'sport_stream_13b',
        'sport_stream_14b',
        'sport_stream_15b',
        'sport_stream_16b',
        'sport_stream_17b',
        'sport_stream_18b',
        'sport_stream_19b',
        'sport_stream_20b',
        'sport_stream_21b',
        'sport_stream_22b',
        'sport_stream_23b',
        'sport_stream_24b',
        'scotland_stream_01',
        'scotland_stream_02',
        'scotland_stream_03',
        'scotland_stream_04',
        ]:
        items.append({
            'label': "%s" % channelname,
            'path': plugin.url_for('devices', channelname=channelname),

        })

    return items


@plugin.route('/devices/<channelname>')
def devices(channelname):
    items = []
    items.append({
        'label': "%s ALL" % channelname,
        'path': plugin.url_for('channel', channelname=channelname),

    })
    for device in sorted(['abr_hdtv', 'hdtv', 'tv', 'hls_tablet', 'pc', 'apple-ipad-hls''pc','iptv-all', 'apple-ipad-hls']):
        items.append({
            'label': "%s %s" % (channelname,device),
            'path': plugin.url_for('device', channelname=channelname, device='pc'),

        })
    return items

@plugin.route('/play/<id>')
def play(id):
    headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1"}

    url = "http://www.bbc.co.uk/iplayer/episode/%s" % id
    r = requests.get(url, headers=headers)
    html = r.content
    vpid = re.compile('"vpid":"(.+?)"').findall(html)
    vpid = vpid[0]
    url = "http://ess.api.bbci.co.uk/schedules?versionId=%s" % vpid
    r = requests.get(url, headers=headers)
    html = r.content
    match = re.search('"(sport_stream_.*?)"',html)
    channelname = match.group(1)

    items = device(channelname,'abr_hdtv')
    bitrate = plugin.get_setting('olympics')
    if bitrate == "0":
        return items
    else:
        url = items[int(bitrate)]['path']
        play_media(url)
        #return [items[int(bitrate)-1]]

@plugin.route('/olympics')
def olympics():
    headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1"}
    url = "http://www.bbc.co.uk/iplayer/group/p04375l6"
    r = requests.get(url,headers=headers)
    html = r.content
    match = re.findall('href="/iplayer/episode/(p.*?)/.*?".*?title="(.*?)"',html,flags=(re.DOTALL | re.MULTILINE))
    items = []
    for (id,title) in match:
        items.append(    {
            'label': HTMLParser.HTMLParser().unescape(title.decode('utf-8')),
            'path': plugin.url_for('play',id=id),
            'thumbnail':get_icon_path('tv'),
        })
    return items


@plugin.route('/')
def index():
    items = [
    {
        'label': 'Olympics',
        'path': plugin.url_for('olympics'),
        'thumbnail':get_icon_path('tv'),
    },
    ]
    return items


if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        plugin.set_view_mode(view_mode)