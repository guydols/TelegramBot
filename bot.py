from telegram.ext.dispatcher import run_async
from telegram.ext import CommandHandler
from telegram.ext import Updater
from bs4 import BeautifulSoup
import urllib.request
import logging
import random
import pickle
import time
import os


class Telegram():

    def __init__(self):

        # setup logging
        log_file = 'bot.log'
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)
        self.logger = logging.getLogger('bot')
        self.logger.setLevel(level=logging.INFO)
        self.logger.addHandler(handler)

        self.hdrs={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}

        self.ledger = {}
        self.srcs = [
            {'src': 'https://old.reddit.com/r/meme/',
            'type': 'image', 'buffer': []},
            {'src': 'https://old.reddit.com/r/dankmemes/',
            'type': 'image', 'buffer': []},
            {'src': 'https://old.reddit.com/r/youtubehaiku/',
            'type': 'video', 'buffer': []},
            {'src': 'https://old.reddit.com/r/Wellthatsucks/',
            'type': 'image', 'buffer': []}]

        self.text = {'start': '''Commands:
            Use /meme to get random meme in random formats.
            Use /image to get random meme in an image.
            Use /video to get random meme in an video.
            Use /stats to see stats about the current chat.'''}

        self.checkfiles()

		# Fill token with api key from telegram
        updater = Updater(
            token='') 
        dispatcher = updater.dispatcher
        jobs = updater.job_queue

        job_minute = jobs.run_repeating(self.callbackMinute, interval=60, first=0)

        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)

        meme_handler = CommandHandler('meme', self.meme)
        dispatcher.add_handler(meme_handler)

        image_handler = CommandHandler('image', self.image)
        dispatcher.add_handler(image_handler)

        video_handler = CommandHandler('video', self.video)
        dispatcher.add_handler(video_handler)

        stats_handler = CommandHandler('stats', self.stats)
        dispatcher.add_handler(stats_handler)

        updater.start_polling()

    def checkfiles(self):
        if(os.path.exists('data/srcs') and
        os.path.exists('data/ledger')):
            self.loadAll()

    def callbackMinute(self, bot, job):
        for idx, lst in enumerate(self.srcs):
            urllist = self.scrape(lst['src'], 25)
            bufflist = []
            for link in urllist:
                if not self.inBuffer(link):
                    bufflist.append(link)
            self.srcs[idx]['buffer'] = self.srcs[idx]['buffer'] + bufflist
        self.saveAll()

    def start(self, bot, update):
        cid = update.message.chat_id
        self.logger.info('Recieved /start command from {}'.format(cid))
        bot.send_message(chat_id=cid, text=self.text['start'])

    @run_async
    def meme(self, bot, update):
        cid = update.message.chat_id
        self.logger.info('Recieved /meme command from {}'.format(cid))
        res = self.getRandom(cid)
        bot.send_message(chat_id=cid, text=res)

    @run_async
    def image(self, bot, update):
        cid = update.message.chat_id
        self.logger.info('Recieved /image command from {}'.format(cid))
        res = self.getImage(cid)
        bot.send_message(chat_id=cid, text=res)

    @run_async
    def video(self, bot, update):
        cid = update.message.chat_id
        self.logger.info('Recieved /video command from {}'.format(cid))
        res = self.getVideo(cid)
        bot.send_message(chat_id=cid, text=res)

    @run_async
    def stats(self, bot, update):
        cid = update.message.chat_id
        self.logger.info('Recieved /stats command from {}'.format(cid))
        res = "Served {} memes to this chat.".format(len(self.ledger[cid]))
        bot.send_message(chat_id=cid, text=res)

    def saveAll(self):
        with open('data/srcs', 'wb') as f:
            pickle.dump(self.srcs, f, pickle.HIGHEST_PROTOCOL)
        with open('data/ledger', 'wb') as f:
            pickle.dump(self.ledger, f, pickle.HIGHEST_PROTOCOL)

    def loadAll(self):
        with open('data/srcs', 'rb') as f:
            self.srcs = pickle.load(f)
        with open('data/ledger', 'rb') as f:
            self.ledger = pickle.load(f)

    def getRandom(self, cid):
        rng = random.SystemRandom()
        dic = rng.choice(self.srcs)
        url = rng.choice(dic['buffer'])
        if not self.memeInChat(cid, url):
            return url
        else:
            return self.getRandom(cid)

    def getImage(self, cid):
        rng = random.SystemRandom()
        dlist = []
        for lst in self.srcs:
            if lst['type'] == 'image':
                dlist.append(lst)
        dic = rng.choice(dlist)
        url = rng.choice(dic['buffer'])
        if not self.memeInChat(cid, url):
            return url
        else:
            return self.getImage(cid)

    def getVideo(self, cid):
        rng = random.SystemRandom()
        dlist = []
        for lst in self.srcs:
            if lst['type'] == 'video':
                dlist.append(lst)
        dic = rng.choice(dlist)
        url = rng.choice(dic['buffer'])
        if not self.memeInChat(cid, url):
            return url
        else:
            return self.getVideo(cid)

    def inBuffer(self, link):
        for lst in self.srcs:
            if link in lst['buffer']:
                return True
        return False

    def memeInChat(self, cid, data):
        try:
            for element in self.ledger[cid]:
                if data == element[0]:
                    return True
            self.ledger[cid].append([data, time.time()])
        except KeyError:
            self.ledger[cid] = []
            self.ledger[cid].append([data, time.time()])
            return False
        return False

    def scrape(self, url, nposts):
        if 'reddit.com' in url:
            return self.reddit(url, nposts)

    def parser(self, url):
        opener = urllib.request.build_opener()
        req = urllib.request.Request(url, headers=self.hdrs)
        html = opener.open(req).read()
        return BeautifulSoup(html, 'html.parser')

    def reddit(self, url, nposts):
        posts = []
        if nposts <= 25:
            soup = self.parser(url)
            table = soup.find('div', {'id': 'siteTable'})
            divs = table.find_all('div', {'class': 'thing'})
            for div in divs:
                posts.append(div['data-url'])
            return posts
        else:
            pass


if __name__ == '__main__':
    memebot = Telegram()
