"""AScript app facade for the Summoners War reroll runner."""

from .core.run_state import RunMode
from .runner import Runner


def run():
    from ascript.android.ui import Dialog

    selected = Dialog.select(
        ["联动活动（15成就召唤书）", "火山（光暗召唤书）"],
        msg="请选择本次脚本目标",
        title="刷取模式",
        submit="开始",
        cancel="取消",
    )
    if selected is None:
        print("[runner] mode selection cancelled")
        return
    run_mode = (
        RunMode.COLLABORATION if selected == 0 else RunMode.VOLCANO
    )
    print("[runner] selected mode: {}".format(run_mode))
    Runner(run_mode=run_mode).run_forever()
