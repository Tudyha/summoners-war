# 画面驱动自动化架构

## 核心原则

脚本采用“感知 → 决策 → 动作 → 重新感知”的反应式循环。

1. 画面是当前事实，流程状态只提供上下文。
2. 遮挡层优先于主画面业务动作。
3. 每轮只允许一个行为取得执行权；动作后必须重新采集画面。
4. 终局、主城和支援列表等画面具有所有权，可阻止低优先级识别误点。
5. 通用“确认”最后处理，流程专属确认由对应流程优先处理。

## 目录职责

```text
summoners-war/
├── runner.py          依赖组装和行为优先级
├── config.py          坐标、阈值和运行参数
├── core/              画面模型、识别、状态、路由和主循环
├── flows/             按业务画面划分的动作流程
├── vision/            OCR 与 OpenCV 视觉检测器
├── platform/          AScript 设备操作和应用生命周期
├── integrations/      飞书等外部服务
└── tests/             不依赖真机的纯逻辑测试
```

## 运行链路

```text
AutomationEngine
    ├─ begin_visual_frame()              清空本轮截图缓存
    ├─ observe()                         采集本轮 OCR
    ├─ recognize_scene()                 生成主画面及识别证据
    ├─ recognize_overlays()              识别遮挡层及业务所有权
    ├─ ScreenSnapshot                    固化本轮决策输入
    └─ PriorityRouter.tick()
         ├─ chat_overlay
         ├─ global_overlay
         ├─ nickname_field               精确控件输入
         ├─ nickname                     独占等待游戏内确认
         ├─ endgame                      独占流程
         ├─ tutorial_arrow               强制引导优先于主城默认动作
         ├─ home                         主城所有权
         ├─ support_overlay              支援列表所有权
         ├─ world_map
         ├─ tutorial_overlay
         ├─ generic_tutorial_text
         ├─ dialogue
         ├─ startup
         ├─ battle_preparation
         ├─ battle_result
         ├─ battle_runtime
         ├─ generic_confirm              必须靠后
         └─ idle_friend_request
```

路由器遇到第一个非 `NO_MATCH` 结果后立即结束本轮，后续行为不会执行。

## 行为结果

- `NO_MATCH`：当前行为不负责这个画面。
- `ACTED`：已经执行动作，本轮必须结束。
- `RUNNING`：行为拥有当前流程，正在等待后续画面。
- `BLOCKED`：满足画面但缺少安全执行条件。
- `FAILED`：行为执行失败，由运行监督器记录和恢复。

`HandlerBehavior` 将 Flow 的“是否执行动作”结果转换为统一行为结果；具有画面所有权的行为即使暂时没有动作，也会返回 `RUNNING` 并阻止低优先级误点。

## 组合边界

`Runner` 只负责创建依赖和声明路由顺序，不包含 OCR 规则、坐标或业务步骤。它组合以下独立对象：

- `DeviceActions`：唯一的点击、滑动、输入和无障碍节点操作入口。
- `StartupFlow`：条款、服务器、游客登录和资源下载。
- `OverlayFlow`：活动、购买、礼包及通用确认。
- `TutorialFlow`：黄色箭头、教程遮罩和剧情对话。
- `WorldMapFlow`：地图推进和终局切换。
- `BattleFlow`：关卡、队伍、支援、战斗和结算。
- `HomeFlow`：主城所有权及任务继续。
- `FriendFlow`：聊天和好友申请。
- `EndgameFlow`：邮箱、光暗召唤和游戏初始化。
- `NicknameFlow`：无障碍昵称输入。

Flow 通过显式传入的 `RunnerState` 和 `DeviceActions` 访问状态与副作用，也可以调用纯识别器和配置；不得直接导入 AScript 平台操作模块。

## 状态边界

`RunnerState` 将状态按职责分组：

- `runtime`：最后动作、最后画面、最后行为和连续错误。
- `friend`：好友请求时间、候选游标和禁用状态。
- `battle`：队伍、支援选择以及关卡列表滚动。
- `world_map`：地图搜索和返回任务状态。
- `nickname`：固定昵称值、输入重试和游戏内确认阶段。
- `endgame`：邮箱、光暗召唤、召唤阵搜索和重置。
- `stop`：五星停止和重置前停止。

终局阶段使用 `EndgamePhase` 明确表示 `INACTIVE / SUMMON / RESET / RESET_CONFIRM`，不再混用布尔值和字符串。项目已移除 Mixin、扁平状态代理和 Runner 隐式共享字段。

## 视觉边界

- `vision/core.py`：OCR Observation、分辨率和每轮截图缓存。
- `vision/map.py`：世界地图和主城召唤阵候选。
- `vision/battle_runtime.py`：战斗目标和自动战斗。
- `vision/stage.py`：关卡、队伍和战斗控件。
- `vision/support.py`：支援魔灵列表。
- `vision/battle.py`：上述三个模块的兼容导出门面。
- `vision/tutorial.py`：教程箭头、遮罩、高亮和剧情对话。
- `vision/friend.py`：聊天入口。
- `vision/startup.py`：游客登录。
- `vision/overlay.py`：弹窗关闭图标。
- `vision/__init__.py`：旧 `.vision` 调用方的兼容导出门面，不存放实现。

同一决策轮次中的 OpenCV 检测共享一张延迟获取的截图。动作执行后进入下一轮，缓存失效并重新采集。

## 新增画面

1. 在 `core/screen_model.py` 的 `Scene` 增加画面常量。
2. 在 `core/scene_recognizer.py` 添加至少两个相互独立的识别证据。
3. 在 `tests/test_scene_recognizer.py` 加入命中和误判样本。
4. 编写只处理该画面的行为，并放到正确的路由优先级。
5. 危险点击必须再次确认画面特征和按钮区域。

## 新增弹窗

先判断弹窗所有权：

- 全局安全弹窗：加入 `handle_global_overlays()`。
- 业务专属弹窗：加入对应业务行为，不进入通用确认。
- 未知确认弹窗：默认不处理；只有建立标题、按钮区域和排除条件后才能加入白名单。

弹窗识别证据和所有权同时登记在 `core/overlay_recognizer.py`，业务处理逻辑仍放在对应行为中。

关闭弹窗后只返回 `ACTED`，不得继续使用旧画面执行原业务动作。

## 测试

纯逻辑测试不依赖 AScript：

```bash
python -m unittest discover -v
```

提交到设备前还应执行：

```bash
python -m compileall -q .
```

涉及坐标、颜色阈值、动画时序或 AScript API 的改动仍必须在真机验证。
