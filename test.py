import os, sys, tempfile, threading, time, types

# stub renasync so the addon can be imported and tested standalone
renasync = types.ModuleType('renasync')
client = types.ModuleType('renasync.client')

client.online = []
client.player = None
client.ignoreurl = False
client.command = {}

def _print(*args):
	client._out.append(' '.join(map(str, args)))

client._out = []
client.print = _print

def _log(text):
	# mirrors renasync.client.log: timestamp via the module-level print
	client.print(f'[{time.strftime("%H:%M")}] {text}')

client.log = _log

def _handlemessage(msg):
	if msg.startswith('/bogus'):
		client.log('Invalid chat command!')
	elif msg.startswith('/privmsg'):
		client.log(f"Could not send message to 'bob'!")

client.handlemessage = _handlemessage
client.send = lambda *a: None
client.main = lambda *a: None
client.command['load'] = lambda user, target, path: None

renasync.client = client
sys.modules['renasync'] = renasync
sys.modules['renasync.client'] = client

os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from renasync_gui import App, Args, configdir, load_config, save_config

# config + parse
cfg = {'saved': [{'server': 'ws://x:9', 'room': 'a', 'name': 'b'}]}
save_config(cfg)
assert load_config() == cfg
assert configdir() == os.path.join(os.environ['XDG_CONFIG_HOME'], 'renasync')
assert App.parse(None, '<alice> hello') == ('alice', 'hello')
assert App.parse(None, '(alice -> me) pst') == ('alice', 'pst')
assert App.parse(None, "'bob' has joined the room") == (None, None)
print('[ok] config + parse')

# log patch: hooked log pipes through the original and captures lines
received = []
orig = client.log

def hooked(text):
	try:
		orig(text)
	except:
		pass
	received.append(text)

client.log = hooked
client.handlemessage('/bogus')
assert received[-1] == 'Invalid chat command!'
client.handlemessage('/privmsg bob hello')
assert received[-1] == "Could not send message to 'bob'!"
print('[ok] log patch')

# print patch: log output lands in the module-level print
client._out.clear()
client.log('echo')
assert client._out and client._out[0].endswith('echo'), client._out
print('[ok] print patch')

class StubList:
	def __init__(self): self.items = []
	def delete(self, *a): self.items = []
	def insert(self, *a): self.items.append(a[1])
	def curelems(self): return ()
	def current(self, i=None): return 0 if self.items else -1
	def set(self, v): self.value = v
	def __setitem__(self, k, v): self.values = v

class StubVar:
	def __init__(self): self.v = ''
	def set(self, v): self.v = v
	def get(self): return self.v
	def delete(self, *a): self.v = ''
	def insert(self, *a): self.v = a[1]

save_config({'saved': []})

def newapp():
	app = App.__new__(App)
	app.saved = StubList()
	return app

args = Args(); args.server = 'ws://x'; args.room = 'r'; args.name = 'n'
app = newapp()
App.remember(app, args)
App.remember(app, args)
g2 = Args(); g2.server = 'ws://y'; g2.room = 'r'; g2.name = 'n'
App.remember(app, g2)
saved = load_config()['saved']
assert len(saved) == 2 and saved[0] == {'server': 'ws://x', 'room': 'r', 'name': 'n'}

app = newapp(); app.saved.items = ['x']
app.vars = {k: StubVar() for k in ('Server', 'Room', 'Name')}
App.use(app)
assert app.vars['Server'].v == 'ws://x' and app.vars['Name'].v == 'n'
assert app.vars['Room'].v == 'r'

app = newapp(); app.saved.items = ['x']
App.forget(app)
saved = load_config()['saved']
assert len(saved) == 1 and saved[0]['server'] == 'ws://y'
print('[ok] remember / use / forget')

# last used preset fills the dialog on open; nothing saved -> blank
app = newapp(); app.saved.items = ['x']
app.vars = {k: StubVar() for k in ('Server', 'Room', 'Name')}
App.remember_last(app, g2)
App.autoselect(app)
assert app.vars['Server'].v == 'ws://y' and app.vars['Name'].v == 'n'
save_config({'saved': []})
app = newapp(); app.saved.items = []
app.vars = {k: StubVar() for k in ('Server', 'Room', 'Name')}
App.autoselect(app)
assert app.vars['Server'].v == '' and app.vars['Name'].v == ''
save_config({'saved': [], 'last': ['ghost', 'ghost', 'ghost']})
app = newapp(); app.saved.items = []
app.vars = {k: StubVar() for k in ('Server', 'Room', 'Name')}
App.autoselect(app)
assert app.vars['Name'].v == '', 'stale last preset must not fill fields'
print('[ok] remember last + autoselect')

# playlist
from urllib.parse import unquote as _unquote

class StubBox:
	def __init__(self): self.items = []
	def delete(self, *a): self.items = []
	def insert(self, *a): self.items.append(a[1])
	def curselection(self): return ()

class FakePlayer:
	def __init__(self): self.played = []
	def play(self, url): self.played.append(url)
	def observe_property(self, *a, **k): pass

def makeapp(me='a'):
	app = App.__new__(App)
	app.pbox = StubBox()
	app.autonext = type('V', (), {'get': lambda s: True})()
	app.items = []
	app.playidx = -1
	app.me = me
	app.sends = []
	app.broadcast = lambda op: app.sends.append(op)
	return app

client.player = FakePlayer()
app = makeapp()
App.papply(app, {'op': 'add', 'url': 'http://x/f1.mp4'})
App.papply(app, {'op': 'add', 'url': 'http://x/f2.mp4'})
assert app.items == ['http://x/f1.mp4', 'http://x/f2.mp4']
App.papply(app, {'op': 'play', 'index': 1})
assert app.playidx == 1
assert client.player.played[-1] == 'http://x/f2.mp4'
print('[ok] playlist: add + play loads local player')

app.playidx = 0
App.advance(app, app.playidx)
assert app.sends[-1] == {'op': 'play', 'index': 1}
assert client.player.played[-1] == 'http://x/f2.mp4'
# stale end event from an already-replaced item must be ignored
app.playidx = 1
App.advance(app, 0)
assert app.sends[-1] == {'op': 'play', 'index': 1}, 'stale advance must not skip ahead'
assert app.playidx == 1
print('[ok] playlist: advance broadcasts + plays next, stale events ignored')

app.items = ['a', 'b', 'c']; app.playidx = 2
App.papply(app, {'op': 'remove', 'index': 2})
assert app.items == ['a', 'b'] and app.playidx == -1
app.items = ['a', 'b', 'c']; app.playidx = 1
App.papply(app, {'op': 'remove', 'index': 0})
assert app.items == ['b', 'c'] and app.playidx == 0
App.papply(app, {'op': 'clear'})
assert app.items == [] and app.playidx == -1
print('[ok] playlist: remove adjusts index, clear empties')

app.sends.clear()
App.papply(app, {'op': 'sync'})
# empty queue -> no sync response
assert app.sends == []
app.items = ['http://x/f1.mp4']; app.playidx = 0
client.online = ['b']
App.papply(app, {'op': 'sync'})
assert app.sends and app.sends[-1]['op'] == 'set' and app.sends[-1]['items'] == app.items
app2 = makeapp(me='b')
app2.items = ['http://x/a.mp4']
client.online = ['a']
app2.sends.clear()
App.papply(app2, {'op': 'sync'})
assert app2.sends == [], 'non-host must not respond'
print('[ok] playlist: sync answered only by the lexicographically first member')

# our own broadcast echoing back must be ignored (kills the double-add bug)
app = makeapp(me='a')
app.to_main = lambda func, *a: func(*a)
App.handle_playlist(app, 'a', 'everyone', {'op': 'add', 'url': 'http://x/z.mp4'})
assert app.items == [], 'self-echo must be ignored'
App.handle_playlist(app, 'b', 'everyone', {'op': 'add', 'url': 'http://x/z.mp4'})
assert app.items == ['http://x/z.mp4'], 'other users must apply'
print('[ok] playlist: self-echo ignored, others apply')

# urls render decoded, untruncated in the playlist view
app = makeapp()
app.pbox.delete(-1, -1)
app.items = ['http://x/o%20ku.mp4?x=1', 'https://manji.lvx.red/A/%E6%AD%BB%E7%A5%9E/01.mp4']
App.refresh_playlist(app)
assert app.pbox.items[0] == 'o ku.mp4', app.pbox.items
assert app.pbox.items[1] == '01.mp4', app.pbox.items
app.items = ['https://x/' + 'a' * 30 + '.mp4']
App.refresh_playlist(app)
assert app.pbox.items[0] == 'a' * 30 + '.mp4', app.pbox.items
print('[ok] playlist: urls decoded, untruncated in view')

# folder-aware load: a same-named local file is resolved against the last browsed folder
tmp = tempfile.mkdtemp()
open(os.path.join(tmp, 'Ep02.mkv'), 'wb').write(b'x')

captured = []
client.command['load'] = lambda user, target, path: captured.append((user, target, path))

app = App.__new__(App)
app.folder = tmp
app.to_main = lambda *a: None
app.me = 'me'
app.lock = threading.Lock()
app.failed = ''
app.connected = False

App.install(app)

client.command['load']('bob', 'me', 'Ep02.mkv')
assert captured and captured[0][2] == os.path.join(tmp, 'Ep02.mkv'), captured

# urls pass through untouched
captured.clear()
client.command['load']('bob', 'me', 'https://x/Ep02.mkv')
assert captured and captured[0][2] == 'https://x/Ep02.mkv', captured

# no folder learned yet -> nothing changes
captured.clear()
app2 = App.__new__(App)
app2.folder = ''
App.install(app2)
client.command['load']('bob', 'me', 'missing.mkv')
assert captured and captured[0][2] == 'missing.mkv', captured
print('[ok] folder-aware load fallback')

print('ALL PASS')