# Panasonic Smart China ZY Custom for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/badge/version-2.2.1-blue.svg)]()

面向中国区「松下智能家电」App 的 Home Assistant 自定义集成，重点适配 **CS-ZY35K410**（洵风系列，2024 AirconCommon 新协议）。域名 `panasonic_smart_china_zy`，不与原版 `panasonic_smart_china` 冲突。

## 协议依据

| 来源 | 说明 |
|---|---|
| `https://app.psmartcloud.com/ca/cn/0900/AirconCommon/` | 官方 H5 控制页，主包 `static/js/app.*.js` + **26 个懒加载 `chunk-*.js`** 才构成完整字段字典 |
| `ACDevGetStatusInfoAW` / `ACDevSetStatusNewProtocol` | 状态读取 / 控制端点 |
| 瀚思彼岸论坛 17153 帖 43# | `runStatus` 48/49、`runMode` 65–69、风速与扫风枚举的实测记录 |
| `panasonic_smart_china` v3.0.0 `profiles/split_ac_0900_airconcommon.py` | 同一协议的社区逆向成果，用于校验能力门控与用电统计端点 |
| **本机实机状态（2026-11-06）** | 温度刻度、`*Ex` 能力位、5 个辅助端点返回结构均经真实响应核对 |

设备 token 由 `deviceId` 经双重 SHA-512 推导，已对本机实测值校验一致，**无需抓包，也无需反编译 APK**。

## 安装

HACS：添加本仓库为自定义仓库（类别 Integration）→ 搜索 `Panasonic Smart China ZY Custom` → 下载 → 重启 HA。
手动：复制 `custom_components/panasonic_smart_china_zy` 到 `/config/custom_components/`，重启后添加集成。

> 松下账号是**单点登录**。HA 登录后手机 App 会掉线；手机重新登录又会让 HA 会话失效。会话失效时集成会提示「重新登录松下账号」，重新输入密码即可，设备 ID 与已有实体 ID 不变。

## 实体清单（合计 33 个）

| 平台 | 实体 | 状态字段 / 端点 | 门控 |
|---|---|---|---|
| climate ×1 | 空调 | `runStatus` / `runMode` / `setTemperature` / `windSet` / `portraitWindSet` / `orientationWindSet` | — |
| switch ×10 | 电源、强劲运转、自清洁、柔湿制冷、辅热、纳诺怡、睡眠、显示灯、空间净化、**定时开关** | `highCool` / `cleanSet` / `cool` / `elecHeat` / `nanoe` / `lamp` / `spaceClean` / `fixTimeStatus` | `*Ex` 能力位 |
| select ×3 | 场景、上下扫风位置、左右扫风位置 | `scene` / `portraitWindSet` / `orientationWindSet` | 左右扫风由 `leftType` 门控 |
| button ×2 | 电源切换、滤网复位 | `runStatus` / `filterReset` | — |
| sensor ×14 | 回风温度、故障码、今日用电量/时长/费用、本月用电量/时长/费用、本年用电量/费用、制冷/制暖/抽湿记忆温度、**定时计划** | 状态 bean + `ACGetElectricChargeTodayInfo` / `ACGetElectricChargeDaylyInfo` / `ACGetAirconYearGraphInfo` / `ACGetModeTempInfo` / `ACGetAirconTimerNewProtocol` | — |
| binary_sensor ×2 | 故障、滤网需更换 | `alarmCode` / `filterReset` | — |
| number ×1 | **电价**（元/kWh，可写） | `ACGetAirconElectricChargeInfo` / `ACSetAirconElectricChargeInfo` | — |

剩余实体仍由 `*Ex` 能力位门控；能力位为 0 或状态字段缺失时会显示为「不可用」，这是硬件不支持的正常表现。本机 `spaceCleanEx=1`，**空间净化是真实支持的功能**（`spaceClean=0` 表示当前关闭），不要误删。

2.2.1 已从本机型 profile 中移除 3 个实机确认不支持的实体：`UVC 除菌`（`uvcEx=0`、状态无 `uvc` 字段）、`语音提示`（`voiceSetEx=0`、状态无 `voiceSet` 字段）、`新风运行`（`ervType=0`，无新风模块）。这三者在 HA 里会变成孤儿实体，需一并删除。

### climate 可用值

- 模式：自动(65)、制冷(66)、制热(67)、除湿(68)、送风(69)、关机
- 风速：Auto(65)、Min(49)、Low(50)、Medium(52)、High(54)、Max(55)，对应 App 的自动/20%/40%/60%/80%/100%
- 上下扫风：Auto(70)、方向 1–5(65/68/67/69/66)
- 左右扫风：Auto(64)、最左(66)、偏左(108)、正对(67)、偏右(87)、最右(65)
- 场景：关闭(64)、怡静风(65)、超远风(66)、环抱风(67)

### App 配色（模式色值）

官方 `RUN_MODE_COLOR` 是**前端配色表**，不是设备上报的数据，因此不单独建实体，而是作为 climate 的额外属性提供，供卡片动态配色：

| 属性 | 示例 | 说明 |
|---|---|---|
| `mode_color` | `#4097DC` | 自动 `#DDD` / 制冷 `#4097DC` / 制暖 `#FF9E18` / 抽湿 `#00C101` / 送风 `#7056DC`，关机回落 `#DDD` |
| `mode_color_name` | 蓝色 | 中文颜色名 |
| `mode_label` | 制冷 | 中文模式名 |
| `run_mode_raw` | `66` | 原始 `runMode` 值 |

```yaml
{{ state_attr('climate.<你的空调实体>', 'mode_color') }}
```

### 定时（2.2.0 新增）

协议取自官方 `TimingSettingPage` / `ParmSetPage`，并已用实机响应（2026-11-06）核对：

| 端点 | 用途 |
|---|---|
| `ACGetAirconTimerNewProtocol` | 返回 `weekList`（周一~周日），每天一个 `timerList` |
| `ACGetAirconFixTimeStatusInfo` | 返回 `fixTimeStatus`：**1=启用 / 0=停用** |
| `ACSetAirconFixTimeStatusInfo` | 写入 `params: {fixTimeStatus: 1}`；扁平格式会返回 `4099 缺少请求参数` |
| `ACSetAirconTimerNewProtocol` | 修改定时条目（本集成**不调用**） |

`startTime = 60×小时 + 分钟`（180=03:00、503=08:23）；`runStatus` 48=开机 / 49=关机；`runMode` 65–69 与 climate 一致。

- `switch.…定时开关`：唯一可写的定时实体，等同 App 定时页的总开关。
- `sensor.…定时计划`：state 为已配置的定时条数，属性含 `enabled`、`schedule`（星期 / 时间 / 动作 / 模式 / 温度 / 纳诺怡）、`next_timer`（下一次将执行，含 `days_ahead`）。

> 定时条目本身**只读**。`ACSetAirconTimerNewProtocol` 会按 `*Ex` 能力位裁剪字段，误写会静默覆盖 App 里配好的计划，因此不提供增删改；要改计划请仍在 App 里操作。

## 架构

- **单设备单轮询**：所有实体共享一个 `PanasonicStatusCoordinator`（15s）与一个 `PanasonicAuxCoordinator`（60s），不再每个实体各发一次云端请求。
- **Read-Modify-Write**：控制前重新读取最新状态，只回写 `AIRCONCOMMON_SAFE_KEYS` 中实机确认的 24 个可写字段；能力位、只读诊断值、一次性指令不回显。官方 App 每条指令固定带 `buzzer=65`（提示音标记，非开关），集成同样处理。
- **认证失效**：识别顶层 `errorCode` 与嵌套 `error.code`（3003/3004/403/4102），触发 HA 重新认证流程，不再静默失败。
- **温度刻度**：实机 `setTemperature=27` 对应 27℃，确认本机为 **x1**；集成仍保留自动判断（>45 视为 x2）以兼容其他固件。
- **设备归组**：所有实体带 `DeviceInfo`，在 HA 中归入同一个设备卡片。

## 已知限制

| 项目 | 状态 |
|---|---|
| 定时开关机 | **2.2.0 已接入**：总开关可写、每周计划只读展示；定时条目的增删改未提供（避免误写覆盖 App 计划） |
| 新风独立 fan 实体 | 本机 `ervType=0`（无新风模块），2.2.1 起不再注册「新风运行」实体 |
| `highWarm` / `nanoeX` 独立开关 | **刻意不做**：官方用同一 `highCool` 按制冷/制热派生「强智冷/强智暖」；`nanoeX` 与 `nanoe` / `o2Set` / `runMode` 是联动状态机，单独写会破坏联动 |
| 单点登录 | 无法规避，需通过重新认证刷新 SSID |
| 云端自签名证书 | 请求使用 `ssl=False`；如 HA 环境限制，请检查网络策略 |

## 升级说明

从 1.1.0 / 1.2.1 升级到 2.x 时，**域名、设备 ID、全部 unique_id 均保持不变**，现有自动化与仪表盘无需改动。

2.1.0 移除了 6 个在官方协议与实机状态中均不存在的历史实体（`displaySet` / `sleepMode` / `powerfulMode` / `cleanMode` 四个 select、`buzzer` switch、`selfcleanReset` button），它们在 HA 里会变成孤儿实体，可在「实体」页面删除。新增的电价、本年费用、模式记忆温度会自动出现。

2.2.0 新增「定时开关」switch 与「定时计划」sensor，复用现有 60s 辅助轮询，不增加云端请求频率；升级后自动出现，无需重新配置。

2.2.1 清理：移除 UVC 除菌、语音提示、新风运行 3 个本机型不支持的实体定义（36→33），并在 HA 中删除 13 个 1.1.0 / 2.1.0 遗留孤儿实体，共清理 16 条注册表记录。删除前会备份 `/config/.storage/core.entity_registry`；若需恢复，改回代码重启后实体会重新注册（entity_id 可能变化）。

建议升级前备份 `/config/custom_components/panasonic_smart_china_zy`。本仓库保留了 `backup/v1.1.0` 分支与 `backup-v1.1.0-before-completion` 标签，可随时回滚。
