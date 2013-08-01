import time

from irc.client import *
from irc.bot import SingleServerIRCBot, ServerSpec
from camxes import camxes, ParsingError

class CamxesBot(SingleServerIRCBot):
    def __init__(self, server_list, join_list, nickname='camxes', realname='Camxes'):
        SingleServerIRCBot.__init__(self, server_list, nickname, realname)
        self.join_list = join_list
    
    def start(self):
        SingleServerIRCBot._connect(self)
        for j in self.join_list:
            self.connection.join(j)
        SimpleIRCClient.start(self)


    def get_camxes(self, text):
        try:
            return camxes(text)
        except ParsingError:
            return 'Irregular camxes.jar output: Does your sentence have a \'=\' or \'(...)\' ?'
        except Exception as e:
            return str(e)


    def on_pubmsg(self, conn, ev):
        text = ev.arguments[0]
        if len(text) > 6 and text[:6] == 'camxes' and text[6] in [':',',',' ']:
            self.on_msg(ev.target, text[7:])
        
    def on_privmsg(self, conn, ev):
        target = ev.source[:ev.source.find('!')]
        self.on_msg(target, ev.arguments[0])

    def on_msg(self, target, text):
        self.connection.privmsg(target, self.get_camxes(text))

if __name__=='__main__':
    servers = [ServerSpec('irc.freenode.net')]
    joins = ['#munje', '#lojban', '#ckule']
    stop = False
    while not stop:
        stop = True
        try:
            camxes_bot = CamxesBot(servers, joins)
            camxes_bot.start()
        except KeyboardInterrupt:
            stop = True
        except Exception as e:
            print(e)
        del camxes_bot
        time.sleep(120)
