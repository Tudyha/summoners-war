"""App lifecycle helpers."""

import time

from ascript.android import action, system

from . import config
from .vision import observe, scale_point


def ensure_game():
    try:
        current = system.get_foreground_app()
    except Exception as exc:
        print("[startup] foreground check failed: {}".format(exc))
        current = None
    if current == config.GAME_PACKAGE:
        return
    print("[startup] opening {}".format(config.GAME_PACKAGE))
    system.open(config.GAME_PACKAGE)
    system.wait_for_package(config.GAME_PACKAGE, 30000)


def _tap(point_name, reason):
    x, y = scale_point(config.POINTS[point_name])
    action.click(x, y)
    print("[reset] {} at ({}, {})".format(reason, x, y))


def _wait_until(predicate, timeout_seconds, label):
    deadline = time.time() + timeout_seconds
    last_obs = None
    while time.time() < deadline:
        last_obs = observe()
        if predicate(last_obs):
            return last_obs
        time.sleep(0.8)
    if last_obs is None:
        print("[reset] timeout waiting for {}".format(label))
    else:
        print("[reset] timeout waiting for {}: {}".format(
            label,
            last_obs.compact_text(),
        ))
    return None


def _exit_game_to_launcher():
    print("[reset] exiting game with Back key")
    for _ in range(8):
        obs = observe()
        if obs.contains("要结束游戏吗"):
            _tap("exit_game_yes", "confirm game exit")
            time.sleep(2.0)
            return True
        try:
            action.Key.back()
        except Exception as exc:
            print("[reset] Back key failed: {}".format(exc))
            return False
        time.sleep(0.9)

    obs = observe()
    if obs.contains("要结束游戏吗"):
        _tap("exit_game_yes", "confirm game exit")
        time.sleep(2.0)
        return True

    print("[reset] game exit dialog not found; continuing reset route from current screen")
    return False


def _open_app_storage_from_launcher():
    _tap("launcher_settings", "open launcher settings")
    settings = _wait_until(
        lambda obs: obs.contains("应用"),
        8.0,
        "Android settings",
    )
    if settings is None:
        return False

    _tap("settings_apps", "open settings apps")
    apps = _wait_until(
        lambda obs: obs.contains("魔灵召唤"),
        8.0,
        "apps page with Summoners War",
    )
    if apps is None:
        return False

    _tap("settings_recent_game", "open Summoners War app info")
    app_info = _wait_until(
        lambda obs: (
            obs.contains("存储")
            and (
                obs.contains("强行停止")
                or obs.contains("卸载")
                or obs.contains("打开")
            )
        ),
        8.0,
        "Summoners War app info",
    )
    if app_info is None:
        return False

    _tap("app_info_storage", "open app storage")
    storage = _wait_until(
        lambda obs: obs.contains("清空存储空间") or obs.contains("清空存储"),
        8.0,
        "Summoners War storage page",
    )
    return storage is not None


def _clear_storage_on_current_page():
    obs = observe()
    if not (obs.contains("清空存储空间") or obs.contains("清空存储")):
        print("[reset] storage clear button is not visible: {}".format(obs.compact_text()))
        return False

    _tap("storage_clear_data", "open clear app data confirmation")
    confirm = _wait_until(
        lambda current: current.contains("要删除应用数据吗")
        and current.contains("确定"),
        5.0,
        "clear-data confirmation dialog",
    )
    if confirm is None:
        return False

    _tap("storage_clear_data_confirm", "confirm clear app data")
    cleared = _wait_until(
        lambda current: current.contains("0B")
        or current.contains("0 B")
        or current.contains("OB"),
        10.0,
        "cleared app data",
    )
    return cleared is not None


def reset_game_data():
    print("[reset] resetting game data through verified Android settings UI")
    _exit_game_to_launcher()

    if not _open_app_storage_from_launcher():
        print("[reset] failed to reach app storage page; reopening game without clearing")
        ensure_game()
        return False

    if not _clear_storage_on_current_page():
        print("[reset] failed to clear app data; reopening game")
        ensure_game()
        return False

    print("[reset] app data cleared; reopening game")
    system.open(config.GAME_PACKAGE)
    system.wait_for_package(config.GAME_PACKAGE, 30000)
    return True
