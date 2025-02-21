import configparser
from dataclasses import dataclass
from typing import T, Callable


class FieldType:
    MANUAL_STR = 0

    NUMBER_PICKER = 1
    ITEM_PICKER = 2
    SLIDER = 3
    TOGGLE_SWITCH = 4


class SettingField:
    """
    The SettingField class stores the data for a single field/type of configuration in a collection of settings.
    """

    def __init__(self,
                 field_name: str,
                 field_label: str,
                 field_type: int,

                 default_value: int or float or bool,
                 selection_args: tuple or list[T] or None = None,
                 format_func: None or Callable[[T], str] = str,
                 new_section: None or str = None):

        """
        Params:

        :param field_name: The name of the field referenced by the program.
        :param field_label: The text that is shown when the setting is displayed in a setting panel.

        :param field_type: The type of widget that is shown in the setting panel that also determines the data type of
                           the field. The field type is a very important attribute of this class, as it determines the
                           valid data types of the default_value, selection_args, and format_func attributes/arguments.
                           See the table below for more info.

                           Possible field types are the field type constants, i.e. NUMBER_PICKER, ITEM_PICKER, SLIDER,
                           TOGGLE_SWITCH.

        =======================================
        Valid Arguments According to Field Type
        =======================================

        Field type              Default value               Selection args              Format func

        Manual string    ->     str                         -                           -

        Number Picker    ->     int or float                tuple: (min, max, step)     callable: (int or float) -> str
        Item Picker      ->     int (index of item list)    list: list of items         callable: (type of items) -> str
        Slider           ->     int or float                tuple: (min, max)           -
        Toggle Switch    ->     bool                        -                           -

        :param default_value: The default value of the field.

        :param selection_args: (Varies according to the field type) A tuple or list that gives information about the
                               possible values of the field. See the table above for more info.

        :param format_func: (Only used in number and item pickers) A customizable function that formats/converts the
                            currently selected item or numerical value into a string.
        """

        """
        Validate `selection_args` based on `field_type`.
        
        `default_value` is checked separately by calling the `set_value` method.
        """
        # region Validate
        match field_type:
            case FieldType.MANUAL_STR:
                if selection_args:
                    raise ValueError("manual fields do not have selection args")

            case FieldType.NUMBER_PICKER:
                if (type(selection_args) is not tuple or len(selection_args) != 3 or
                    any(type(x) is not int and type(x) is not float for x in selection_args)):

                    raise TypeError("selection args for a number picker must be a tuple of 3 numbers: (min, max, step), "
                                    f"got: {selection_args}")

            case FieldType.ITEM_PICKER:
                if type(selection_args) is not list:
                    raise TypeError("selection args for an item picker must be a list of selectable items")

            case FieldType.SLIDER:
                if (type(selection_args) is not tuple or len(selection_args) != 2 or
                    any(type(x) is not int and type(x) is not float for x in selection_args)):

                    raise ValueError(
                        "selection args for a slider must be a tuple of 2 numbers: (min, max), "
                        f"got: {selection_args}")

            case FieldType.TOGGLE_SWITCH:
                if selection_args:
                    raise ValueError("toggle switches do not have selection args")

            case _:
                raise ValueError(f"invalid field type id: {field_type}")

        # endregion

        self._field_name = field_name
        self._field_label = field_label
        self._field_type = field_type

        self._value: int or float or bool = default_value
        self._selection_args: tuple or list or None = selection_args
        self.format_func: Callable = format_func
        self.new_section: str or None = new_section

        self.set_value(default_value)  # This is called to validate the default value.

    """
    Getters and setters
    """

    def get_value_to_str(self) -> str:
        return str(self._value)

    def get_value(self, item_picker_index=False) -> int or float or T or bool:
        if self._field_type == FieldType.ITEM_PICKER and not item_picker_index:
            return self._selection_args[self._value]
        else:
            return self._value

    def set_value_from_str(self, value: str) -> None:
        if self._field_type == FieldType.TOGGLE_SWITCH and type(value) is not bool:
            if value == "True":
                value = True
            elif value == "False":
                value = False
            else:
                raise ValueError(f"invalid boolean value for toggle switch: {value}")

        elif self._field_type != FieldType.MANUAL_STR:
            value = float(value)
            value = int(value) if value.is_integer() else value

        self.set_value(value)

    def set_value(self, value):
        match self._field_type:
            case FieldType.MANUAL_STR:
                if type(value) is not str:
                    raise TypeError(f"the value type for manual strings must be str, got: {value}")

            case (FieldType.NUMBER_PICKER, FieldType.SLIDER):
                if type(value) is not int or type(value) is not float:
                    raise TypeError("the value type for number pickers and sliders must be either int or float, "
                                    f"got: {value}")

            case FieldType.ITEM_PICKER:
                if type(value) is not int:
                    raise TypeError("the value type for item pickers must be an int representing a list index"
                                    f"got: {value}")

                elif not 0 <= value < len(self._selection_args):
                    raise IndexError(f"the given index is out of range: {value}")

            case FieldType.TOGGLE_SWITCH:
                if type(value) is not bool:
                    raise TypeError(f"the value type for toggle switches must be bool, got: {value}")

        self._value = value

    @property
    def field_name(self):
        return self._field_name

    @property
    def field_label(self):
        return self._field_label

    @property
    def field_type(self):
        return self._field_type

    @property
    def selection_args(self):
        return self._selection_args


class SettingsData:
    """
    The SettingsData class enables the program to store data for a single collection of settings. The data can then be
    fetched and used by any part of the program, displayed using a setting panel widget, and be saved into a ".ini" file
    using the configparser module.
    """

    def __init__(self, *fields: SettingField, save_path: str = "", auto_load=True):
        super().__init__()

        self._field_dict = {x.field_name: x for x in fields}
        self._save_path = save_path

        if auto_load:
            self.load()

    def get_value(self, field_name: str) -> T:
        return self._field_dict[field_name].get_value()

    def set_value(self, field_name: str, value: int or float or bool):
        self._field_dict[field_name].set_value(value)

    def save(self):
        config = configparser.ConfigParser()

        for field_name, field in self._field_dict.items():
            config["DEFAULT"][field_name] = field.get_value_to_str()

        with open(self._save_path, "w") as f:
            config.write(f)

    def load(self):
        try:
            config = configparser.ConfigParser()
            config.read(self._save_path)
        except FileNotFoundError:
            return 1
        except configparser.ParsingError:
            return 2

        for field_name, field in self._field_dict.items():
            try:
                field.set_value_from_str(config["DEFAULT"][field_name])

            except (KeyError, TypeError, IndexError, ValueError):
                pass

        return 0

    @property
    def field_dict(self):
        return self._field_dict
