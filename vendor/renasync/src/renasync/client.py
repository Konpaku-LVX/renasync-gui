#!/usr/bin/env python3
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

import ipaddress
import argparse
import atexit
import shlex
import json
import time
import ssl
import os

# abstractions

class Lock:
	locked = False

	def pick(self):
		state = self.locked
		self.locked = False
		return state

	def lock(self):
		self.locked = True

class MessageList:
	mlist = []
	mspan = []

	limit = 3
	span = 30

	def add(self, msg):
		# get current time
		epoch = time.time()

		# add message
		self.mlist.append(msg)
		self.mspan.append(epoch)

		# message limit
		if len(self.mlist) > self.limit:
			self.mlist.pop(0)
			self.mspan.pop(0)

		# trim old messages
		while epoch - self.mspan[0] > self.span:
			self.mlist.pop(0)
			self.mspan.pop(0)

	def get(self):
		return '\n'.join(self.mlist)

# state

online = []
loader = 'everyone'

messages = MessageList()
loadLock = Lock()
seekLock = Lock()
pauseLock = Lock()
pauseLock.lock()

# helpers

def ip4(addr):
	# check if address is a valid IPv4
	try:
		return ipaddress.IPv4Address(addr)
	except:
		return None

def ip6(addr):
	# check if address is a valid IPv6
	try:
		return ipaddress.IPv6Address(addr)
	except:
		return None

def wss(addr, port):
	# add missing fields to address
	if ip4(addr):
		return f'ws://{addr}:{port}'

	if ip6(addr):
		return f'ws://[{addr}]:{port}'

	if ':' not in addr:
		return f'wss://{addr}:{port}'

	return addr

def sanitize(path):
	# strip absolute paths
	if path and os.path.isabs(path):
		return os.path.basename(path)

	return path

def console(prompt):
	# prepare console prompt
	player.script_message_to('console', 'type', prompt)

def display(text):
	# show text for duration
	player.show_text(text, 10000)

def log(text):
	# log to terminal
	ts = time.strftime('%H:%M')
	print(f'[{ts}] {text}')

	# display recent messages
	messages.add(text)
	display(messages.get())

def current(online):
	# show online users
	text = ', '.join(online)
	log(f'Currently online: {text}')

def send(cmd, val, target='everyone'):
	# build command
	msg = {
		'to': target,
		'cmd': cmd,
		'val': val
	}

	msg = json.dumps(msg)
	msg = msg.encode()

	# send to server
	websock.send(msg)

# protocol commands

def load(user, target, path):
	global loader

	# validate input
	if not isinstance(path, str):
		return

	# set loader
	loader = target

	# sanitize path
	path = sanitize(path)

	# log command
	log(f"{user} has loaded '{path}'")

	# ignore self
	if user == name:
		return

	# try to seek to the start
	if player.seekable:
		seekLock.lock()
		player.seek(0, 'absolute', 'exact')

	# avoid reloading same media
	if path == sanitize(player.path):
		return

	# skip links if ignoring them
	if '://' in path and ignoreurl:
		return

	# open links and files that exist
	if '://' in path or os.path.isfile(path):
		loadLock.lock()
		player.play(path)

def seek(user, target, timestamp):
	# validate input
	if not isinstance(timestamp, float):
		return

	# log command
	log(f'{user} has seeked to {timestamp:.2f}')

	# ignore self
	if user == name:
		return

	# only seek if possible
	if not player.seekable:
		return

	# only seek if needed
	if timestamp != player.time_pos:
		seekLock.lock()
		player.seek(timestamp, 'absolute', 'exact')

def pause(user, target, state):
	# validate input
	if not isinstance(state, bool):
		return

	# log command
	text = 'yes' if state else 'no'
	log(f'{user} has set pause to {text}')

	# ignore self
	if user == name:
		return

	# only pause if needed
	if state != player.pause:
		pauseLock.lock()
		player.pause = state

def query(user, target, prop):
	# ignore self
	if user == name:
		return

	# define property to send
	if prop == 'load':
		val = sanitize(player.path)
	elif prop == 'seek':
		val = player.time_pos
	elif prop == 'pause':
		val = player.pause
	else:
		return

	# send video player state
	send(prop, val, target=user)

def message(user, target, msg):
	# validate input
	if not isinstance(msg, str):
		return

	# format message accordingly
	if target == 'everyone':
		text = f'<{user}> {msg}'
	else:
		text = f'({user} -> {name}) {msg}'

	# log command
	log(text)

def join(user, target, who):
	# validate input
	if not isinstance(who, str):
		return

	# only system allowed
	if user != 'system':
		return

	# log command
	log(f"'{who}' has joined the room")

	# add others to list
	if who != name:
		online.append(who)

def leave(user, target, who):
	# validate input
	if not isinstance(who, str):
		return

	# only system allowed
	if user != 'system':
		return

	# log command
	log(f"'{who}' has left the room")

	# remove user from list
	online.remove(who)

command = {
	'load': load,
	'seek': seek,
	'pause': pause,
	'query': query,
	'message': message,
	'join': join,
	'leave': leave
}

# chat commands

def privmsg(arg):
	# validate length
	if len(arg) < 2:
		return

	# parse arguments
	user = arg[0]

	msg = arg[1:]
	msg = ' '.join(msg)

	# send private message
	if user in online:
		log(f'({name} -> {user}) {msg}')
		send('message', msg, target=user)
	else:
		log(f"Could not send message to '{user}'!")

def loadto(arg):
	# validate length
	if len(arg) != 2:
		return

	# parse arguments
	user = arg[0]
	path = arg[1]

	# send load command
	if user in online:
		log(f"Telling '{user}' to load '{path}'...")
		send('load', path, target=user)
	else:
		log(f"Could not tell '{user}' to load '{path}'!")

def loadfrom(arg):
	# validate length
	if len(arg) != 1:
		return

	# parse arguments
	user = arg[0]

	# send query command
	if user in online:
		log(f"Requesting state from '{user}'...")
		send('query', 'load', target=user)
	else:
		log(f"Could not request state from '{user}'!")

chatcmd = {
	'privmsg': privmsg,
	'loadto': loadto,
	'loadfrom': loadfrom
}

def chatcommand(msg):
	# parse command
	msg = shlex.split(msg)

	if not msg:
		return

	cmd = msg[0]
	arg = msg[1:]

	# only run valid commands
	if cmd in chatcmd:
		chatcmd[cmd](arg)
	else:
		log('Invalid chat command!')

def handlemessage(msg):
	# skip empty string
	if not msg:
		return

	# handle type of message
	if msg[0] == '/':
		chatcommand(msg[1:])
	else:
		send('message', msg)

# mpv callbacks

def on_load(ev):
	if not loadLock.pick():
		send('load', sanitize(player.path))

def on_seek(ev):
	if not seekLock.pick():
		send('seek', player.time_pos)

def on_pause(name, value):
	if not pauseLock.pick():
		send('pause', player.pause)

def on_start(ev):
	global loader

	# not loaded from a query
	if loader == 'everyone':
		return

	# reset loader state
	loader = 'everyone'

	# no one to help
	if not online:
		return

	# query some user for missing state
	send('query', 'pause', target=online[0])
	send('query', 'seek', target=online[0])

def on_msg(ev):
	# parse mpv message
	msg = ev.as_dict()
	msg = msg['args']

	if msg[0] != b'input-event':
		return

	if msg[1] != b'submit':
		return

	msg = json.loads(msg[2])[0]

	# send to handler
	handlemessage(msg)

def on_enter():
	player.script_message_to(
		'console',
		'get-input',
		'py_event_handler',
		'{"prompt": "> "}'
	)

def on_tab():
	current([name] + online)

def on_colon():
	global ignoreurl

	# toggle ignoration flag
	ignoreurl = not ignoreurl

	# notify the user about it
	text = 'yes' if ignoreurl else 'no'
	log(f'Ignore URLs: {text}')

def on_quote():
	console('loadfile ')

def on_console():
	console('')

def on_quit(ev):
	if websock:
		websock.close()

# client

def loop(websock, name):
	# listen for commands
	for msg in websock:
		# parse command
		op = json.loads(msg)

		user = op['from']
		target = op['to']
		cmd = op['cmd']
		val = op['val']

		# only run implemented commands
		if cmd in command:
			command[cmd](user, target, val)
		else:
			print(f'Command {cmd} not implemented!')

def login(websock, name, room):
	global online

	# send login message
	login = {
		'user': name,
		'room': room
	}

	login = json.dumps(login)
	login = login.encode()

	websock.send(login)

	# receive list of online users
	msg = websock.recv()
	online = json.loads(msg)

	# show online users
	current(online)

	# query some user for file to load
	if online:
		send('query', 'load', target=online[0])

	# listen for commands
	loop(websock, name)

# procedures

def arguments(parser):
	parser.description = 'Synchronize playback between video player instances (client)'

	parser.add_argument('-n', '--name', help='username of choice', required=True)
	parser.add_argument('-r', '--room', help='name of the room to join', required=True)
	parser.add_argument('-s', '--server', help='address of the server', required=True)
	parser.add_argument('--no-verify', help='skip certificate verification', action='store_true')
	parser.add_argument('--ignore-url', help='ignore links sent in rooms', action='store_true')

	return parser

def main(args):
	global name
	global player
	global websock
	global ignoreurl

	# set up globals
	websock = None
	name = args.name
	ignoreurl = args.ignore_url

	# add current directory to path (yt-dlp/DLLs)
	os.environ['PATH'] += os.pathsep + os.getcwd()

	# start up mpv
	import mpv

	player = mpv.MPV(
		config=True,
		input_default_bindings=True,
		input_vo_keyboard=True,
		osc=True,
		hr_seek=True,
		keep_open=True,
		keep_open_pause=False,
		msg_level='all=fatal',
		player_operation_mode='pseudo-gui'
	)

	# set up mpv callbacks
	player.event_callback('start-file')(on_load)
	player.event_callback('seek')(on_seek)
	player.property_observer('pause')(on_pause)
	player.event_callback('file-loaded')(on_start)
	player.event_callback('client-message')(on_msg)
	player.on_key_press('ENTER')(on_enter)
	player.on_key_press('TAB')(on_tab)
	player.on_key_press(':')(on_colon)
	player.on_key_press('\'')(on_quote)
	player.on_key_press('`')(on_console)
	player.event_callback('shutdown')(on_quit)

	# add tls verification skip
	tls = None

	if args.no_verify:
		tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
		tls.check_hostname = False
		tls.verify_mode = ssl.CERT_NONE

	# add missing fields to address
	address = wss(args.server, 9999)

	try:
		# attempt to connect and login
		print(f'Connecting to {address}')
		with connect(address, ssl=tls) as websock:
			login(websock, args.name, args.room)
	except KeyboardInterrupt:
		# interrupt not considered an error
		print('Ctrl-c received! Closing client...')
	except ConnectionClosed:
		# connection closed means username is taken
		print('Failed to login: Username already taken')
	except ConnectionRefusedError:
		# connection refused means server does not exist
		print('Failed to connect: Invalid server')
	except Exception:
		# make nt console hang
		if os.name == 'nt':
			atexit.register(input, 'Press ENTER to close...')

		raise
	finally:
		# close mpv window
		player.terminate()

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser = arguments(parser)
	args = parser.parse_args()
	main(args)
