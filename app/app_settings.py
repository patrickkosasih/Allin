import os
from app.tools.settings_data import SettingField, SettingsData, FieldType
from app.shared import SAVE_FOLDER_PATH


"""
App Settings

1. Audio
    * Music volume
    * SFX volume

2. Graphics
    * Windowed
    * Window resolution
    * FPS limit

3. Interface
    * Start-up sequence
    * Background
"""
main = SettingsData([
    # region Audio
    SettingField("music_volume", "Music Volume", FieldType.SLIDER,
                 0.75, (0.0, 1.0),
                 new_section="Audio"),

    SettingField("sfx_volume", "SFX Volume", FieldType.SLIDER,
                 1.0, (0.0, 1.0)),
    # endregion

    # region Graphics
    SettingField("windowed", "Windowed", FieldType.TOGGLE_SWITCH,
                 False,
                 new_section="Graphics"),

    SettingField("window_resolution", "Window Resolution", FieldType.ITEM_PICKER,
                 1, [(960, 540), (1280, 720), (1366, 768), (1920, 1080)],
                 format_func=lambda x: f"{x[0]} × {x[1]}"),

    SettingField("fps_limit", "FPS Limit", FieldType.ITEM_PICKER,
                 3, [0, 30, 45, 60, 90, 120, 144, 240],
                 format_func=lambda x: "Unlimited" if x == 0 else str(x)),
    # endregion

    # region Interface
    SettingField("startup_sequence", "Start-up Sequence", FieldType.TOGGLE_SWITCH,
                 True,
                 new_section="Interface"),

    SettingField("show_bg", "Background Art", FieldType.TOGGLE_SWITCH,
                 True),

    SettingField("card_highlights", "Card Highlights", FieldType.ITEM_PICKER,
                 2, ["off", "ranked_only", "all", "all_always"],
                 format_func=lambda x: {"off": "Off",
                                        "ranked_only": "Ranked cards only",
                                        "all": "Entire hand",
                                        "all_always": "Entire hand always"}[x]),
    # endregion

], os.path.join(SAVE_FOLDER_PATH, "app_settings.ini"))
