from app.widgets.basic.panel import Panel
from app.widgets.widget import Widget


class RoomDisplay(Widget):
    pass


class RoomsPanel(Panel):
    def __init__(self, parent, *rect_args, **kwargs):
        super().__init__(parent, *rect_args, **kwargs)

