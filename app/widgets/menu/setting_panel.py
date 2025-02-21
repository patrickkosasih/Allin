from app.scenes.scene import Scene
from app.shared import *
from app.tools.settings_data import SettingsData, SettingField, FieldType
from app.widgets.basic.number_picker import NumberPicker, ItemPicker
from app.widgets.basic.slider import Slider
from app.widgets.basic.toggle_switch import ToggleSwitch
from app.widgets.widget import Widget, WidgetComponent
from app.widgets.basic.panel import Panel


DEFAULT_ENTRY_BG_COLOR = (20, 20, 20, 128)
DEFAULT_ENTRY_FG_COLOR = (255, 255, 255)


class SettingEntry(Widget):
    """
    Setting fields are elements of the setting panel which has a representing text and an input widget.
    """

    def __init__(self, parent: "SettingPanel", *rect_args,
                 entry_label_text: str = "",
                 field_data: SettingField or None = None,
                 call_on_change: Callable[[], None] = lambda: None,

                 horizontal_margin=2,
                 entry_base_color=DEFAULT_ENTRY_BG_COLOR,
                 entry_label_scale=0.6,
                 entry_label_color=DEFAULT_ENTRY_FG_COLOR):

        super().__init__(parent, *rect_args)

        self.field_data: SettingField = field_data
        self._call_on_change: Callable[[], None] = call_on_change

        self.horizontal_margin = horizontal_margin

        self.base = WidgetComponent(self, 0, 0, 100, 100, "%", "ctr", "ctr")
        draw_rounded_rect(self.base.image, self.base.rect, color=entry_base_color)

        self.label = WidgetComponent(self, horizontal_margin, 0, 50, 100, "%", "ml", "ml")
        self.label.image = (FontSave.get_font(self.rect.height * entry_label_scale, "px").
                            render(entry_label_text, True, entry_label_color))

        self.input_widget: None or NumberPicker or ItemPicker or Slider or ToggleSwitch
        self.input_widget = None
        self.input_widget_code = 0

    def set_input_widget(self, widget_type: int, **widget_kwargs):
        if self.input_widget:
            del self.input_widget

        self.input_widget_code = widget_type

        match widget_type:
            case FieldType.MANUAL_STR:
                self.input_widget = None

            case FieldType.NUMBER_PICKER:
                self.input_widget = NumberPicker(self, -self.horizontal_margin, 0, 25, 75, "%", "mr", "mr",
                                                 call_on_change=self.on_change, **widget_kwargs)

            case FieldType.ITEM_PICKER:
                self.input_widget = ItemPicker(self, -self.horizontal_margin, 0, 30, 75, "%", "mr", "mr",
                                               call_on_change=self.on_change, **widget_kwargs)

            case FieldType.SLIDER:
                self.input_widget = Slider(self, -self.horizontal_margin, 0, 50, 75, "%", "mr", "mr",
                                           call_on_change=self.on_change, **widget_kwargs)

            case FieldType.TOGGLE_SWITCH:
                self.input_widget = ToggleSwitch(self, -self.horizontal_margin, 0, 100, 50, ("%", "%h"), "mr", "mr",
                                                 call_on_change=self.on_change, **widget_kwargs)

            case _:
                raise ValueError(f"invalid widget type code: {widget_type}")

    def get_entry_data(self, item_picker_index=False):
        match self.input_widget_code:
            case FieldType.NUMBER_PICKER:
                return self.input_widget.value

            case FieldType.ITEM_PICKER:
                if item_picker_index:
                    return self.input_widget.value
                else:
                    return self.input_widget.selected_item

            case FieldType.SLIDER:
                return self.input_widget.current_value

            case FieldType.TOGGLE_SWITCH:
                return self.input_widget.state

    def on_change(self):
        if self.field_data:
            self.field_data.set_value(self.get_entry_data(item_picker_index=True))

        self._call_on_change()

    @property
    def call_on_change(self):
        return self._call_on_change

    @call_on_change.setter
    def call_on_change(self, call_on_change: Callable[[], None]):
        self._call_on_change = call_on_change

class SettingHeaderLabel(Widget):
    def __init__(self, parent: "SettingPanel", *rect_args, header_text: str, color=DEFAULT_ENTRY_FG_COLOR):
        super().__init__(parent, *rect_args)

        self.image = FontSave.get_font(self.rect.h, "px").render(header_text, True, color)

    def set_input_widget(self, widget_type: int, **widget_kwargs):
        pass


class SettingPanel(Panel):
    """
    The setting panel is an extension of the `Panel` class that is able to contain a collection of configurations that
    can be changed by the player.

    The setting panel can be bound with a `SettingsData` object that stores the data of the setting panel.
    """

    def __init__(self, parent: "Widget" or Scene, *rect_args, panel_unit="%",
                 settings_data: SettingsData or None = None,
                 main_header_str: str = "",
                 entry_horizontal_margin=5, **kwargs):

        super().__init__(parent, *rect_args, panel_unit=panel_unit, **kwargs)

        self.entry_hz_margin = entry_horizontal_margin
        self._entries = {}  # {field name: entry widget}

        self._settings_data: SettingsData = settings_data

        if main_header_str:
            self.add_header(main_header_str)
        if settings_data:
            self.add_entries_from_data()

    def add_entry(self, field_name: str, label_text: str = "", **entry_kwargs) -> SettingEntry:
        if field_name in self._entries:
            raise ValueError(f"field name already exists: {field_name}")

        entry = SettingEntry(self, *self.next_pack_rect, "px", "tl", "tl",
                             entry_label_text=label_text, horizontal_margin=self.entry_hz_margin,
                             **entry_kwargs)

        self.add_scrollable(entry)
        self._entries[field_name] = entry

        return entry

    def add_header(self, header_text: str, font_scale=1.0) -> SettingHeaderLabel:
        x, y, w, h = self.next_pack_rect
        h *= font_scale

        header = SettingHeaderLabel(self, x, y, w, h, "px", "tl", "tl", header_text=header_text)
        self.add_scrollable(header)

        self._next_row_y += self._inner_margin

        return header

    def get_data_as_dict(self) -> dict:
        return {field: entry.get_entry_data() for field, entry in self._entries.items()}

    def add_entries_from_data(self):
        field_name: str
        field: SettingField

        for field_name, field in self._settings_data.field_dict.items():
            if field.field_type == FieldType.MANUAL_STR:
                continue
            if field.new_section:
                self.add_header(field.new_section, font_scale=0.85)

            entry = self.add_entry(field_name, field.field_label, field_data=field)

            match field.field_type:
                case FieldType.NUMBER_PICKER:
                    min_value, max_value, step = field.selection_args

                    entry.set_input_widget(
                        FieldType.NUMBER_PICKER, min_value=min_value, max_value=max_value, step=step,
                        default_value=field.get_value(), format_func=field.format_func
                    )

                case FieldType.ITEM_PICKER:
                    entry.set_input_widget(
                        FieldType.ITEM_PICKER, items=field.selection_args,
                        default_index=field.get_value(item_picker_index=True), format_func=field.format_func
                    )

                case FieldType.SLIDER:
                    min_value, max_value = field.selection_args

                    entry.set_input_widget(
                        FieldType.SLIDER, min_value=min_value, max_value=max_value, default_value=field.get_value()
                    )

                case FieldType.TOGGLE_SWITCH:
                    entry.set_input_widget(
                        FieldType.TOGGLE_SWITCH, default_state=field.get_value()
                    )

    @property
    def settings_data(self):
        return self._settings_data

    @property
    def entries(self) -> dict:
        return self._entries
