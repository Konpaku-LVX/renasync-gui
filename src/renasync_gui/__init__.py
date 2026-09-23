#!/usr/bin/env python3
import atexit
import json
import os
import re
import sys
import threading
import time
import traceback
from urllib.parse import unquote

# tkinter is only required to run the gui
try:
	import tkinter as tk
	from tkinter import ttk, filedialog, messagebox
	import tkinter.font as tkfont
except ImportError:
	tk = None

from renasync import client

WS = 'ws://127.0.0.1:9999'
MAX = 20
SIZE = 12
PALETTE = ['#e06c75', '#61afef', '#98c379', '#c678dd', '#56b6c2', '#e5c07b', '#d19a66']

class Args:
	pass

# configuration

def configdir():
	if os.name == 'nt':
		base = os.environ.get('APPDATA') or os.path.expanduser('~')
	else:
		base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')

	return os.path.join(base, 'renasync')

def configpath():
	return os.path.join(configdir(), 'config.json')

def load_config():
	try:
		with open(configpath()) as file:
			return json.load(file)
	except:
		return {}

def save_config(cfg):
	os.makedirs(configdir(), exist_ok=True)

	path = configpath()
	tmp = path + '.tmp'

	with open(tmp, 'w') as file:
		json.dump(cfg, file, indent='\t')

	os.replace(tmp, path)

# gui

class App:
	def __init__(self, root):
		root.title('Renasync')
		root.minsize(440, 300)
		root.protocol('WM_DELETE_WINDOW', root.destroy)

		# set a fixed point size for the default fonts
		for name in ('TkDefaultFont', 'TkTextFont'):
			font = tkfont.nametofont(name)
			font.configure(size=SIZE)

		self.root = root
		self.me = ''
		self.server = ''
		self.room = ''
		self.connected = False
		self.quitting = False
		self.failed = ''
		self.lock = threading.Lock()
		self.nicks = {}
		self.attached = False
		self.items = []
		self.playidx = -1
		self.folder = ''

		self.build_connect()

	# connect view

	def build_connect(self):
		main = ttk.Frame(self.root, padding=10)
		main.grid(sticky='nsew')
		main.columnconfigure(1, weight=1)

		self.connect = main

		# saved connections
		self.saved = ttk.Combobox(main, state='readonly', width=28)
		self.saved.grid(row=0, column=1, columnspan=2, sticky='ew', pady=(0, 8))
		self.saved.bind('<<ComboboxSelected>>', self.use)

		ttk.Button(main, text='Forget', command=self.forget).grid(row=0, column=3, pady=(0, 8))

		# connection fields
		self.vars = {}

		for i, key in enumerate(('Server', 'Room', 'Name')):
			ttk.Label(main, text=key).grid(row=1 + i, column=0, sticky='e')

			var = tk.StringVar()
			var.trace_add('write', self.update_join)

			entry = ttk.Entry(main, textvariable=var, width=28)
			entry.grid(row=1 + i, column=1, columnspan=3, sticky='ew', padx=4, pady=2)
			entry.bind('<Control-a>', self.select_all)

			self.vars[key] = var

		# options
		self.options = {}

		var = tk.BooleanVar(value=False)
		ttk.Checkbutton(main, text='Remember', variable=var).grid(row=4, column=1, columnspan=3, sticky='w')

		self.options['Remember'] = var

		self.joinbtn = ttk.Button(main, text='Join', command=self.join)
		self.joinbtn.state(['disabled'])
		self.joinbtn.grid(row=5, column=1, columnspan=3, pady=(10, 0))

		self.refresh_saved()
		self.autoselect()
		self.update_join()

	# room view

	def build_room(self):
		self.connect.destroy()

		self.root.minsize(800, 560)
		self.root.geometry('800x560')
		self.root.title('Renasync - ' + self.me)
		self.root.protocol('WM_DELETE_WINDOW', self.close)

		self.root.columnconfigure(0, weight=1)
		self.root.rowconfigure(1, weight=1)

		# toolbar
		bar = ttk.Frame(self.root, padding=(10, 6, 10, 0))
		bar.grid(row=0, column=0, columnspan=2, sticky='ew')

		ttk.Button(bar, text='Load file...', command=self.pick).pack(side='left')

		self.ignore = tk.BooleanVar(value=False)
		ttk.Checkbutton(bar, text='Ignore URLs', variable=self.ignore, command=self.toggle).pack(side='left', padx=(10, 0))

		# body with chat and side panel
		body = ttk.Frame(self.root, padding=10)
		body.grid(row=1, column=0, columnspan=2, sticky='nsew')
		body.columnconfigure(0, weight=1)
		body.rowconfigure(0, weight=1)

		# draggable vertical split between chat and the side panels
		drag = ttk.Panedwindow(body, orient='horizontal')
		drag.grid(row=0, column=0, columnspan=2, sticky='nsew')

		chat = ttk.Frame(drag)
		drag.add(chat, weight=3)

		self.chat = tk.Text(chat, state='disabled', wrap='word', font=tkfont.nametofont('TkTextFont'))
		self.chat.pack(side='left', fill='both', expand=True)

		scroll = ttk.Scrollbar(chat, command=self.chat.yview)
		scroll.pack(side='right', fill='y')

		self.chat.configure(yscrollcommand=scroll.set)

		# draggable horizontal split between users and playlist
		side = ttk.Panedwindow(drag, orient='vertical')
		drag.add(side, weight=1)

		self.build_users(side)
		self.build_playlist(side)

		# input
		field = ttk.Frame(body)
		field.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(8, 0))
		field.columnconfigure(0, weight=1)

		self.text = ttk.Entry(field)
		self.text.grid(row=0, column=0, sticky='ew')
		self.text.bind('<Return>', lambda e: self.send())
		self.text.bind('<Control-a>', self.select_all)

		ttk.Button(field, text='Send', command=self.send).grid(row=0, column=1, padx=(6, 0))

		# status bar
		self.status = tk.StringVar(value='Connecting...')

		ttk.Label(self.root, textvariable=self.status, anchor='w', padding=(10, 4)).grid(row=2, column=0, columnspan=2, sticky='ew')

	# side panel

	def build_users(self, side):
		users = ttk.Frame(side)
		side.add(users, weight=1)

		users.rowconfigure(1, weight=1)
		users.columnconfigure(0, weight=1)

		ttk.Label(users, text='Online').grid(row=0, column=0, sticky='w')

		self.userbox = tk.Listbox(users, width=22, height=4, font=tkfont.nametofont('TkTextFont'))
		self.userbox.grid(row=1, column=0, sticky='nsew')

	def build_playlist(self, side):
		play = ttk.Frame(side)
		side.add(play, weight=3)

		play.rowconfigure(1, weight=1)
		play.columnconfigure(0, weight=1)

		ttk.Label(play, text='Playlist').grid(row=0, column=0, sticky='w')

		self.pbox = tk.Listbox(play, width=22, height=12, font=tkfont.nametofont('TkTextFont'))
		self.pbox.grid(row=1, column=0, sticky='nsew')
		self.pbox.bind('<Double-Button-1>', lambda e: self.pplay())

		self.autonext = tk.BooleanVar(value=True)
		ttk.Checkbutton(play, text='Auto next', variable=self.autonext).grid(row=2, column=0, sticky='w')

		buttons = ttk.Frame(play)
		buttons.grid(row=3, column=0, sticky='ew', pady=(4, 0))

		ttk.Button(buttons, text='Add URLs...', command=self.padd).pack(side='left')
		ttk.Button(buttons, text='Del', command=self.pdel).pack(side='left')
		ttk.Button(buttons, text='Clear', command=self.pclear).pack(side='left')

	# saved connections

	def refresh_saved(self):
		self.saved['values'] = [f"{entry.get('name', '')} in {entry.get('room', '')} @ {entry.get('server', WS)}"
			for entry in load_config().get('saved', [])]

	def use(self, *_):
		# fill fields from selected entry
		index = self.saved.current()

		if index < 0:
			return

		entry = load_config().get('saved', [])[index]

		for key, var in self.vars.items():
			var.set(entry.get(key.lower(), ''))

	def forget(self):
		# remove selected entry
		index = self.saved.current()

		if index < 0:
			return

		cfg = load_config()
		saved = cfg.get('saved', [])

		del saved[index]

		cfg['saved'] = saved

		save_config(cfg)
		self.saved.set('')
		self.refresh_saved()

	# session

	def update_join(self, *_):
		# enable join when all fields are set
		if all(var.get().strip() for var in self.vars.values()):
			self.joinbtn.state(['!disabled'])
		else:
			self.joinbtn.state(['disabled'])

	def join(self):
		# validate fields
		args = Args()

		args.name = self.vars['Name'].get().strip()
		args.room = self.vars['Room'].get().strip()
		args.server = self.vars['Server'].get().strip()
		args.no_verify = False
		args.ignore_url = False

		if not (args.name and args.room and args.server):
			return

		# save connection if asked to
		if self.options['Remember'].get():
			self.remember(args)

		self.remember_last(args)

		self.me = args.name
		self.server = args.server
		self.room = args.room

		self.build_room()
		self.install()

		self.ignore.set(args.ignore_url)

		threading.Thread(target=self.work, args=(args,), daemon=True).start()
		self.root.after(200, self.attach)

	def remember(self, args):
		proof = (args.server, args.room, args.name)
		cfg = load_config()
		saved = []

		for entry in cfg.get('saved', []):
			if (entry.get('server'), entry.get('room'), entry.get('name')) != proof:
				saved.append(entry)

		saved.append({
			'server': args.server,
			'room': args.room,
			'name': args.name,
		})

		saved = saved[-MAX:]

		cfg['saved'] = saved

		save_config(cfg)
		self.refresh_saved()

	def remember_last(self, args):
		# remember this connection so it opens pre-selected next time
		cfg = load_config()
		cfg['last'] = (args.server, args.room, args.name)
		save_config(cfg)

	def autoselect(self):
		# pre-fill the most recently used saved connection on startup
		last = load_config().get('last')

		if not last:
			return

		for i, entry in enumerate(load_config().get('saved', [])):
			if (entry.get('server'), entry.get('room'), entry.get('name')) == tuple(last):
				self.saved.current(i)
				self.use()
				return

	def install(self):
		# patch client functions to drive the gui
		self.orig_log = client.log
		self.orig_send = client.send

		def hooked(text):
			try:
				self.orig_log(text)
			except:
				pass

			self.to_main(self.log, text)

		def send(cmd, val, target='everyone'):
			with self.lock:
				self.orig_send(cmd, val, target)

		def printing(*args):
			text = ' '.join(map(str, args))

			if text.startswith('Connecting to'):
				self.to_main(self.set_status, 'Connecting...')
			elif 'Failed to' in text:
				self.to_main(self.set_status, text)

				if not self.connected:
					self.failed = text

		# extend the protocol with playlist commands
		client.command['playlist'] = self.handle_playlist

		# resolve same-named local files against the last browsed folder
		self.orig_load = client.command['load']

		def load(user, target, path):
			if (isinstance(path, str)
			    and '://' not in path
			    and not os.path.isfile(path)
			    and self.folder
			    and os.path.isfile(os.path.join(self.folder, os.path.basename(path)))):
				path = os.path.join(self.folder, os.path.basename(path))

			self.orig_load(user, target, path)

		client.command['load'] = load

		client.log = hooked
		client.send = send
		client.print = printing

	def work(self, args):
		# run client main loop
		try:
			client.main(args)
		except:
			# generic failures surface as an error dialog
			self.failed = traceback.format_exc()
			atexit.unregister(input)

		self.to_main(self.ended)

	# session actions

	def pick(self):
		# choose a local file to play and share
		path = filedialog.askopenfilename(parent=self.root)

		if not path:
			return

		self.folder = os.path.dirname(path)

		try:
			player = getattr(client, 'player', None)

			if player:
				player.play(path)
		except:
			pass

	def toggle(self):
		# toggle url filtering
		client.ignoreurl = self.ignore.get()

		text = 'yes' if self.ignore.get() else 'no'
		client.log(f'Ignore URLs: {text}')

	def send(self):
		# send chat or command
		msg = self.text.get().strip()

		if not msg:
			return

		self.text.delete(0, 'end')

		try:
			client.handlemessage(msg)
		except:
			self.append('Could not send message!')

	def close(self):
		# close player and disconnect
		self.quitting = True

		try:
			websock = getattr(client, 'websock', None)

			if websock:
				websock.close()
		except:
			pass

		try:
			player = getattr(client, 'player', None)

			if player:
				player.terminate()
		except:
			pass

		self.root.destroy()

	def ended(self):
		# worker thread finished
		if self.quitting:
			return

		self.quitting = True

		if self.failed:
			messagebox.showerror('Renasync', self.failed, parent=self.root)

		self.root.destroy()

	# playlist

	def broadcast(self, op):
		try:
			client.send('playlist', op)
		except:
			pass

	def handle_playlist(self, user, target, val):
		# ignore our own broadcast echoing back
		if user == self.me:
			return

		self.to_main(self.papply, val)

	def papply(self, op):
		# apply a playlist operation locally
		name = op.get('op')

		if name == 'add':
			self.items.append(op['url'])
		elif name == 'remove':
			index = op['index']

			if not 0 <= index < len(self.items):
				return

			del self.items[index]

			if self.playidx == index:
				self.playidx = -1
			elif self.playidx > index:
				self.playidx -= 1
		elif name == 'clear':
			self.items = []
			self.playidx = -1
		elif name == 'play':
			self.playidx = op['index']
			self.play_at(self.playidx)
		elif name == 'set':
			self.items = list(op.get('items', []))
			self.playidx = op.get('index', -1)
		elif name == 'sync':
			# the first member with a queue shares it with the room
			others = [x for x in getattr(client, 'online', []) if x != self.me]

			if self.items and all(self.me <= x for x in others):
				self.broadcast({'op': 'set', 'items': self.items, 'index': self.playidx})

			return

		self.refresh_playlist()

	def play_at(self, index):
		# play an item from the queue
		if not 0 <= index < len(self.items):
			return

		try:
			player = getattr(client, 'player', None)

			if player:
				player.play(self.items[index])
		except:
			pass

	def attach(self):
		# watch the player for the end of media
		if self.attached or self.quitting:
			return

		player = getattr(client, 'player', None)

		if player:
			try:
				player.observe_property('eof-reached', self.on_eof)
				self.attached = True
				return
			except:
				pass

		self.root.after(200, self.attach)

	def on_eof(self, name, value):
		# advance the playlist when media ends
		if value and self.autonext.get():
			self.to_main(self.advance, self.playidx)

	def advance(self, index):
		# ignore stale end events from an item already replaced
		if index != self.playidx:
			return

		if self.playidx + 1 < len(self.items):
			self.broadcast({'op': 'play', 'index': self.playidx + 1})
			self.papply({'op': 'play', 'index': self.playidx + 1})

	def padd(self):
		# add one or more urls from a dialog
		dialog = tk.Toplevel(self.root)
		dialog.title('Add URLs')
		dialog.transient(self.root)
		dialog.grab_set()

		box = tk.Text(dialog, width=64, height=12, wrap='word')
		box.grid(row=0, column=0, sticky='nsew', padx=(10, 0), pady=(10, 0))

		scroll = ttk.Scrollbar(dialog, command=box.yview)
		scroll.grid(row=0, column=1, sticky='ns', padx=(0, 10), pady=(10, 0))

		box.configure(yscrollcommand=scroll.set)
		dialog.columnconfigure(0, weight=1)
		dialog.rowconfigure(0, weight=1)

		def done():
			urls = [line.strip() for line in box.get('1.0', 'end').splitlines() if line.strip()]

			if not urls:
				return

			dialog.destroy()

			for url in urls:
				self.broadcast({'op': 'add', 'url': url})
				self.papply({'op': 'add', 'url': url})

		def update(*_):
			# only allow adding when something is entered
			if box.get('1.0', 'end').strip():
				addbtn.state(['!disabled'])
			else:
				addbtn.state(['disabled'])

			box.edit_modified(False)

		row = ttk.Frame(dialog)
		row.grid(row=1, column=0, columnspan=2, sticky='e', padx=10, pady=10)

		addbtn = ttk.Button(row, text='Add', command=done)
		addbtn.state(['disabled'])
		addbtn.pack(side='right')
		ttk.Button(row, text='Cancel', command=dialog.destroy).pack(side='right', padx=(0, 6))

		box.bind('<<Modified>>', update)
		box.focus_set()

	def pdel(self):
		# remove the selected item
		select = self.pbox.curselection()

		if not select:
			return

		index = select[0]

		self.broadcast({'op': 'remove', 'index': index})
		self.papply({'op': 'remove', 'index': index})

	def pclear(self):
		# clear the queue
		self.broadcast({'op': 'clear'})
		self.papply({'op': 'clear'})

	def pplay(self):
		# play the selected item, or the current one
		select = self.pbox.curselection()
		index = select[0] if select else self.playidx
		index = index if index >= 0 else 0

		self.broadcast({'op': 'play', 'index': index})
		self.papply({'op': 'play', 'index': index})

	def refresh_playlist(self):
		self.pbox.delete(0, 'end')

		for i, url in enumerate(self.items):
			name = unquote(url.split('?')[0].rsplit('/', 1)[-1]) or url

			if i == self.playidx:
				name = '> ' + name

			self.pbox.insert('end', name)

	# gui helpers

	def to_main(self, func, *args):
		# run a call from any thread safely
		try:
			self.root.after(0, func, *args)
		except:
			pass

	def select_all(self, event):
		# select all text in an entry
		event.widget.select_range(0, 'end')
		event.widget.icursor('end')

		return 'break'

	def log(self, text):
		# append line and maintain user list
		self.append(text)

		if text.startswith('Currently online'):
			self.set_status(f'Connected to {self.server} in {self.room}')
			self.connected = True

			# ask the room for the shared playlist
			self.broadcast({'op': 'sync'})

		self.refresh_users()

	def append(self, text):
		# add colored line to chat
		self.chat.configure(state='normal')

		self.chat.insert('end', f'[{time.strftime("%H:%M")}] ')

		nick, rest = self.parse(text)

		if nick:
			self.chat.insert('end', nick + ': ', (self.tag(nick),))
			self.chat.insert('end', (rest or text) + '\n')
		else:
			self.chat.insert('end', text + '\n')

		self.chat.configure(state='disabled')
		self.chat.see('end')

	def parse(self, text):
		# extract nickname and remainder from a line
		match = re.match(r'^(?:<([^<>]+)>|\(([^<>]+) -> [^)]*\))\s*(.*)$', text)

		if match:
			nick = match.group(1) or match.group(2)

			return nick, match.group(3)

		return None, None

	def tag(self, nick):
		# assign color to a nickname
		if nick not in self.nicks:
			color = PALETTE[sum(map(ord, nick)) % len(PALETTE)]
			tag = 'c' + str(len(self.nicks))

			self.chat.tag_configure(tag, foreground=color)
			self.nicks[nick] = tag

		return self.nicks[nick]

	def refresh_users(self):
		# rebuild online user list
		users = list(getattr(client, 'online', []))

		self.userbox.delete(0, 'end')

		for user in [self.me] + [x for x in users if x != self.me]:
			self.userbox.insert('end', user)

	def set_status(self, text):
		self.status.set(text)

# main

def dlls():
	# make bundled libraries visible on windows
	if os.name != 'nt':
		return

	dirs = [
		getattr(sys, '_MEIPASS', None),
		os.path.dirname(os.path.abspath(sys.executable)),
		os.getcwd(),
	]

	for d in dirs:
		if d and os.path.isdir(d):
			try:
				os.add_dll_directory(d)
			except:
				pass

			os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')

def main():
	# tkinter is required to run the gui
	if tk is None:
		raise ImportError('tkinter is required for the renasync gui')

	dlls()

	root = tk.Tk()
	app = App(root)

	root.mainloop()

if __name__ == '__main__':
	main()