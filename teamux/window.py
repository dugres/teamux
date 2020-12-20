from .base import Base
from .pane import Pane


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
