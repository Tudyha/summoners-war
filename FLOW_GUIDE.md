# 刷光暗初始号脚本维护说明

项目采用画面驱动的组合式行为架构，设计原则和扩展规范见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。

## 卡点对应文件

- 启动、条款、服务器和游客登录：`flows/startup.py`
- 活动、礼包、购买及确认弹窗：`flows/overlay.py`
- 教程箭头、教程文字和剧情对话：`flows/tutorial.py`
- 世界地图推进：`flows/world_map.py`
- 战斗准备、支援、战斗和结算：`flows/battle.py`
- 主城任务和误选建筑恢复：`flows/home.py`
- 聊天好友申请：`flows/friend.py`
- 邮箱、光暗召唤和重置：`flows/endgame.py`
- 昵称输入：`flows/nickname.py`
- 点击、滑动、输入等设备操作：`platform/actions.py`
- 主循环和超时日志：`core/engine.py`
- 行为优先级：`runner.py`

## 视觉识别对应文件

- OCR、分辨率、截图缓存：`vision/core.py`
- 地图和主城候选：`vision/map.py`
- 战斗目标和自动战斗：`vision/battle_runtime.py`
- 关卡、队伍和战斗控件：`vision/stage.py`
- 支援魔灵：`vision/support.py`
- 教程和剧情对话：`vision/tutorial.py`
- 聊天：`vision/friend.py`
- 登录：`vision/startup.py`
- 弹窗关闭图标：`vision/overlay.py`

`vision/__init__.py` 只是兼容门面，不应继续添加新算法。

## 修卡点步骤

1. 读取当前截图、OCR 和运行日志。
2. 判断是主画面、遮挡层还是流程状态问题。
3. 识别失败修改对应 `vision/` 或 `core/*_recognizer.py` 文件。
4. 识别正确但动作错误，修改对应 Flow。
5. 只有真机确认的固定坐标才能加入 `config.POINTS`。
6. 本地运行 `python -m unittest discover -v` 和全量 `py_compile`。
7. 最后由用户同步到设备进行完整流程验证。
