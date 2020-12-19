from collections import namedtuple
from re import search
from subprocess import Popen, PIPE
from time import sleep
from types import SimpleNamespace as ns


class Base:
    fields = None

    def tmux(self, cmd, *args, format=None, target=None):
        cmd = 'tmux', cmd
        if args:
            cmd+=args
        if format:
            cmd+=('-F', format)
        if target:
            cmd+=('-t', target)

        try:
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
            stdout, stderr = proc.communicate()
            ret = proc.returncode
        except Exception as x:
            print(f'\n ! {" ".join(cmd)} \n ! {x}\n')
            raise RuntimeError

        err = stderr.decode().strip()
        if err:
            print(f'\n ! {" ".join(cmd)} [{ret}]\n ! {err}\n')
            raise RuntimeError

        lines = [line.strip() for line in stdout.decode().split('\n') if line.strip()]

        return lines

    def __getattr__(self, name):
        val = getattr(self.fields, name, None)
        if val is None:
            val = getattr(self.active, name)
        return val

    @classmethod
    def spec(cls):
        if not hasattr(cls, 'nt'):
            keys = [
                k.strip()
                for k in cls.Child.keys.split()
                if k.strip()
            ]
            cls.nt = namedtuple('fields', keys)
        return cls.nt._fields, cls.nt._make

    def format(self, keys):
        fl = ['#{%s}' % k for k in keys]
        sep = '\t'
        return sep.join(fl)

    @property
    def children(self):
        keys, make = self.spec()
        lines = self.tmux(
            self.list_cmd,
            format = self.format(keys),
        )
        for line in lines:
            vals = line.split('\t')
            fields = make(vals)
            yield self.Child(self, fields)

    @property
    def is_active(self):
        isactive = f'{self.__class__.__name__.lower()}_active'
        return getattr(self, isactive)=='1'

    @property
    def active(self):
        for child in self.children:
            if child.is_active:
                return child


class Pane(Base):
    keys = '''
        session_id
        window_id
        pane_id
        pane_active
        pane_index
        pane_width
        pane_height
        pane_title
        pane_pid
        pane_start_command
        pane_start_path
        pane_current_path
        pane_current_command
    '''

    def __init__(self, window, fields):
        self.window = window
        self.fields = fields

    def send(self, keys):
        self.tmux('send-keys', keys)
        self.tmux('send-keys', 'Enter')

    def send_key(self, key):
        self.tmux('send-keys', key)

    def script(self, source):
        for line in source.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                self.send(line)

    @property
    def capture(self):
        return self.tmux('capture-pane', '-p').stdout

    def search(self, pat, line, num):
        found = search(pat, line)
        if found:
            grp = found.groupdict()
            grp['line'] = line
            grp['num'] = num
            return ns(**grp)

    def parse(self, pat, num=-1):
        line = self.capture[num]
        return self.search(pat, line, num)

    def find(self, pat):
        num = 0
        for line in reversed(self.capture):
            num-=1
            found = self.search(pat, line, num)
            if found:
                return found

    def find_all(self, pat):
        for num, line in enumerate(self.capture):
            found = self.search(pat, line, num)
            if found:
                yield found

    def wait(self, pat, msg=None):
        go = True
        while go:
            sleep(1)
            out = self.capture
            if not out: continue
            for line in out[-3:]:
                if search(pat, line):
                    go = False
            # print(pat, '->', out[-3:])
        if msg:
            print(msg)

    def run(self, pane, cmd, exp=None, msg=None):
        self.send(cmd)
        if exp:
            self.wait(exp, msg)

    def __str__(self):
        return f"{self.is_active and '*' or ' '} {self.pane_title}{self.pane_id}"


class Window(Base):
    keys = '''
        session_id
        window_id
        window_name
        window_active
        window_width
        window_height
        window_index
    '''
    Child = Pane
    list_cmd = 'list-panes'


    def __init__(self, session, fields):
        self.session = session
        self.fields = fields

    @property
    def panes(self):
        for pane in self.children:
            if (pane.session_id==self.session_id
                and pane.window_id==self.window_id
            ):
                yield pane

    def select(self, target):
        self.tmux(f'select-pane', target=target)
        return self.pane

    def split(self, hv='h'):
        self.tmux(f'split-window', f'-{hv}')

    @property
    def right(self):
        return self.select('right')

    @property
    def left(self):
        return self.select('left')

    def __str__(self):
        return f"{self.is_active and '*' or ' '} {self.window_name}"


class Session(Base):
    keys = '''
        session_name
        session_active
        session_id
        session_width
        session_height
        session_attached
    '''
    Child = Window
    list_cmd ='list-windows'

    def __init__(self, tmux, fields):
        self.Tmux = tmux
        self.fields = fields

    @property
    def windows(self):
        yield from self.children

    def get(self, name):
        for w in self.windows:
            if w.window_name==name:
                return w

    def new(self, name='xw'):
        self.tmux(f'new-window', '-n', name)
        return self.get(name)

    def __str__(self):
        f = self.fields
        return f"{self.is_active and '*' or ' '} {f.session_name}"


class Tmux(Base):
    Child = Session
    list_cmd = 'list-sessions'

    @property
    def sessions(self):
        yield from self.children

    def get(self, name):
        for s in self.sessions:
            if s.session_name==name:
                return s

    def new(self, name='xs'):
        self.tmux('new-session', '-s', name)
        return self.get(name)

    def __str__(self):
        return 'tmux'

    def tree(self):
        print('tmux')
        for s in self.sessions:
            print(' '*3, s)
            for w in s.windows:
                print(' '*6, w)
                for p in w.panes:
                    print(' '*9, p)

tmux = Tmux()
tmux.tree()
