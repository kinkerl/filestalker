#!/usr/bin/env python

import gtk
import pygtk
pygtk.require("2.0")
import Image
import StringIO
import Image, ImageFont, ImageDraw, ImageChops
from configobj import ConfigObj
import os
from threading import Thread
import time
import pynotify
import gobject
import appindicator
		

pynotify.init('filestalker')

#Initializing the gtk's thread engine
#we NEED this because of the STRANGE (F***ING) thread problem with gtk
gtk.gdk.threads_init()

USERHOME = os.environ["HOME"]
STALKER_DIR = os.path.join(USERHOME, '.filestalker')
CONFIGFILE=os.path.join(STALKER_DIR,'config')



def notify(text):
	pixbuf = gtk.gdk.pixbuf_new_from_file_at_size("/usr/share/icons/ubuntu-mono-dark/scalable/apps/filestalker-idle.svg", 64, 64)
	n = pynotify.Notification('filestalker', text)
	n.set_icon_from_pixbuf(pixbuf)
	n.show()
	
class Sambastalk:
	
	def __init__(self, hostname, share, username, password, domain):
		self.hostname = hostname
		self.share = share
		self.username = username
		self.password = password
		self.domain = domain

	def stalk_samba(self, needle):
		import smbclient as smbclient
		try:
			c = smbclient.SambaClient(server=self.hostname, share=self.share, username=self.username, password=self.password, domain=self.domain)
			lists = c.listdir('/')
		except:
			raise Exception('smberror');
		else:	
			filehits = {} #to remove duplicates
			files_allowed = needle
			for entry in lists:
				entry = entry.lower()
				for allowed in files_allowed:
					if allowed in entry:
						filehits[entry] = None #to remove duplicates
			files = {} 
			for filefolder in filehits:
				mdirs = c.lsdir(filefolder)
				for entry in  mdirs:
					if entry[0][0] != '.' and entry[0]!='Thumbs.db': #ignore those
						files[entry[0]]=filefolder
			return files
			

class Menu:

	def __init__(self, base):
		self.base = base
		self.clean_files()

	def clean_files(self):
		self.files = {}

	def add_file(self, element, path):
		self.files[element] = path

	def generate_menu(self, running, difference):
		menu = gtk.Menu()
		
		if running:
			menuItemStatus = gtk.MenuItem('Status: on')
			menuItemStatus.set_sensitive(False)
			menuItemStatus.show()
			menu.append(menuItemStatus)
			
			menuItemStatusToggle = gtk.MenuItem('Stop')
			#menuItem.set_sensitive(False)
			menuItemStatusToggle.connect('activate',self.base.toggleme)
			menuItemStatusToggle.show()
			menu.append(menuItemStatusToggle)
		else:
			menuItemStatus = gtk.MenuItem('Status: off')
			menuItemStatus.set_sensitive(False)
			menuItemStatus.show()
			menu.append(menuItemStatus)
			
			menuItemStatusToggle = gtk.MenuItem('Start')
			#menuItem.set_sensitive(False)
			menuItemStatusToggle.connect('activate', self.base.toggleme)
			menuItemStatusToggle.show()
			menu.append(menuItemStatusToggle)
		
		sep = gtk.SeparatorMenuItem()
		sep.show()
		menu.append(sep)
		
		menuItemStatusToggle = gtk.MenuItem('mark as read')
		#menuItem.set_sensitive(False)
		menuItemStatusToggle.connect('activate', self.base.mark_as_read)
		menuItemStatusToggle.show()
		menu.append(menuItemStatusToggle)
		
		sep = gtk.SeparatorMenuItem()
		sep.show()
		menu.append(sep)
		
		
		if self.files:
			for element in self.files.keys() :
				menuItemStatus = gtk.MenuItem(element)
				if element in difference:
					menuItemStatus.set_sensitive(True)
				else:
					menuItemStatus.set_sensitive(False)
				menuItemStatus.show()
				menuItemStatus.connect('activate',self.openfolder)
				menu.append(menuItemStatus)
		else:
			menuItemStatusToggle = gtk.MenuItem('--no files found--')
			menuItemStatusToggle.set_sensitive(False)
			menuItemStatusToggle.show()
			menu.append(menuItemStatusToggle)
		
			
		return menu


	def openfolder(self, widget = None):
		self.base.openfolder(self.files[widget.get_children()[0].get_label()])

class Stalker(Thread):

	def __init__(self, config, indicator, base):
		Thread.__init__(self)
				
		self.files_found_last_time = {}
		self.files_found_last_read = {}
		self.config = config
		self.menu = Menu(base)
		self.base = base
				
		
		self.indicator = indicator
		self.running = True
		self.smbstalk = Sambastalk(self.config['server']['hostname'], self.config['server']['share'], self.config['server']['username'],  self.config['server']['password'], self.config['server']['domain'])
		print "stalker ready"
		self.cnt = 100000 #so it will check on startup	
		
		
		
	def run (self):
		print "start"
		self.indicator.set_menu(self.menu.generate_menu(self.running, []))
		while self.running:
			time.sleep(1)
			if self.cnt < int(self.config['stalk']['refresh']):
				self.cnt+=1
				continue
			print "tick"
			self.cnt = 0
			try:
				files = self.smbstalk.stalk_samba(self.config['stalk']['needle'])
			except:
				notify('connection error, stopping now')
				self.stop()
				continue;
			difference = list(set(files.keys()).difference(set(self.files_found_last_read.keys()))) 
			
			
			if difference:
				if self.config['stalk']['notify']:
					notify('i found new files for you, master')
				self.menu.clean_files()
				for element in files.keys():
					self.menu.add_file(element, files[element])

				self.files_found_last_time = files
				
				self.indicator.set_menu(self.menu.generate_menu(self.running, difference))
				self.indicator.set_icon ('filestalker-new')
	def stop(self):
		self.running = False
		self.indicator.set_menu(self.menu.generate_menu(self.running, []))
		self.indicator.set_icon ('filestalker-offline')

		
	def mark_as_read(self):
		self.indicator.set_icon ('filestalker-idle')
		self.files_found_last_read = self.files_found_last_time
		



class Base:
	
	def __init__(self):
		self.config = ConfigObj(CONFIGFILE)

		if not self.config['stalk'].has_key('notify'):
			self.config['stalk']['notify'] = True
		if type(self.config['stalk']['notify']) is str and self.config['stalk']['notify'].lower()  == 'false':
			self.config['stalk']['notify'] = False
		if not type(self.config['stalk']['notify']) is bool:
			self.config['stalk']['notify'] = True

		self.indicator = appindicator.Indicator ("filestalkersmb", 'filestalker-idle', appindicator.CATEGORY_APPLICATION_STATUS)
		self.indicator.set_status (appindicator.STATUS_ACTIVE)

		self.stalker = None


	
	def toggleme(self, widget = None, button = None, time = None, data = None):
		print "toggle"
		if self.stalker and self.stalker.running:
			self.stalker.stop()
			
		else:
			self.stalker = Stalker(self.config, self.indicator, self)
			self.stalker.start()
			#notify('starting')
			
	def mark_as_read(self, widget = None):
		self.stalker.mark_as_read()

	def openfolder(self, folder):
		os.system("xdg-open smb://"+self.config['server']['hostname'] +"/"+ self.config['server']['share']+"/"+folder)





if __name__ == '__main__':
	menu = gtk.Menu()
	base = Base()
	base.toggleme()
	gtk.main()

