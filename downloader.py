#!/usr/bin/python3

########
# Author: /u/anonymous_rocketeer
# THIS PROGRAM COMES WITH ABSOLUTELY NO WARRANTY
# Please download only public domain books ;)
######## 

"""
A Simple Ebook downloading bot. 
Much credit to Joel Rosdahl for his irc package:
https://github.com/jaraco/irc
This bot searches irc.irchighway.net only, and is meant only to streamline the somewhat clunky download process. 
This code is of debatable quality, but as far as I can tell, it works.
Use at your own risk

Calling this program:

python3 downloader.py
OR:

python3 downloader.py <nickname> <searchterm>

KNOWN BUGS: If there are no search results, it hangs forever. Sorry.
"""

#Settings:
#Preferred filetype:
filetype = "mobi" 
#Preferred nickname:
nickname = "" #leave blank to be prompted
#TODO: Set custom path to save file?

import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr
import re
import zipfile
import os
import struct
import sys
import argparse
import shlex
from time import sleep
import jaraco.logging
import six
from six.moves import socketserver
import irc.client


def userselect(filename):
    """
    This reads searchbot's results line by line, 
    outputting only the ones that are in the preferred format
    It then asks the user to make a selection
    If the user declines all entries in the preferred format, 
    it lists all available files regardless of filetype.
    """
    with zipfile.ZipFile(filename, "r") as z:
        with z.open(z.namelist()[0]) as fin:

            answer = "n"

            for line in fin:
                line = str(line)[2:-5]
                if "mobi" in line.lower():
                    answer = input(line + " (y/n?)\n")
                if answer == "y":
                    return line.split("::")[0]
            print("No further .mobi lines. Printing lines in order:")
            print("Please note the first few lines are not valid search results.\n")

    #TODO Fix this mess:
    with zipfile.ZipFile(filename, "r") as z:
        with z.open(z.namelist()[0]) as fin:
            answer = "n"
            for line in fin:
                line = str(line)[2:-5]
                answer = input(line + "(y/n?)\n")
                if answer == "y":
                    return line.split("::")[0]
            print("No further lines. Please search again soon! \n")

class TestBot(irc.bot.SingleServerIRCBot):
    def __init__(self, searchterm, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(
            self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.searchterm = searchterm
        self.received_bytes = 0
        self.havebook = False
        
    def on_nicknameinuse(self, c, e): #handle username conflicts
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)
        self.connection.privmsg(self.channel, "@search " + self.searchterm)
        print("Searching ...\n")

    def on_ctcp(self, connection, event):
        #Handle the actual download
        payload = event.arguments[1]
        parts = shlex.split(payload)

        if len(parts) != 5: #Check if it's a DCC SEND 
            return  #If not, we don't care what it is

        print("Receiving Data:")
        print(payload)
        command, filename, peer_address, peer_port, size = parts
        if command != "SEND":
            return
        self.filename = os.path.basename(filename)
        if os.path.exists(self.filename):
            answer = input(
                "A file named", self.filename,
                "already exists. Overwrite? (y/n)")
            if answer != "y":
                print("Refusing to overwrite. Edit filenames and try again.\n")
                self.die()
                return
            print("Overwriting ... \n")
        self.file = open(self.filename, "wb")
        peer_address = irc.client.ip_numstr_to_quad(peer_address)
        peer_port = int(peer_port)
        self.dcc = self.dcc_connect(peer_address, peer_port, "raw")
        
    def on_dccmsg(self, connection, event):
        data = event.arguments[0]
        self.file.write(data)
        self.received_bytes = self.received_bytes + len(data) 
        ##TODO: Write progress bar here?
        self.dcc.send_bytes(struct.pack("!I", self.received_bytes))

    def on_dcc_disconnect(self, connection, event):
        self.file.close()
        print("Received file %s (%d bytes).\n" % (self.filename,
                                                self.received_bytes))
        #self.connection.quit()
        #Download actual book:
        #Have the user pick which one to download:
        if not self.havebook:
            print("Search Complete. Please select file to download:\n")
            book = userselect(self.filename) 
            self.received_bytes = 0 
            self.connection.privmsg(self.channel, book)
            self.havebook = True
            os.remove(self.filename) #remove the search .zip
            print("Submitting request for " + book)
        else:
            self.die() #end program when the book disconnect finishes

    def search(self, searchterm):
        self.connection.privmsg(self.channel, searchterm)

def main():
    global nickname
    searchterm = ""
    if len(sys.argv) == 3:
        searchterm = sys.argv[1]
        nickname = sys.argv[2]
    else:
        print("Usage: testbot <searchterm> <nickname>")
        searchterm = input("Enter Search Term(s):\n")
        if nickname == "":
            nickname = input("Enter Nickname:\n")

    server = "irc.irchighway.net"
    port = 6667
    channel = "#ebooks"

    bot = TestBot(searchterm, channel, nickname, server, port)
    bot.start()

if __name__ == "__main__":
    main()

