# Panasonic Smart China ZY Custom for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/badge/version-2.3.1-blue.svg)]()

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

## 实体清单（共 35 个定义，默认启用 33 个）

| 平台 | 实体 | 状态字段 / 端点 | 门控 |
|---|---|---|---|
| climate ×1 | 空调 | `runStatus` / `runMode` / `setTemperature` / `windSet` / `portraitWindSet` / `orientationWindSet` | — |
| switch ×10 | 电源、强劲运转、自清洁、柔湿制冷、辅热、纳诺怡、睡眠、显示灯、空间净化、**定时开关** | `highCool` / `cleanSet` / `cool` / `elecHeat` / `nanoe` / `lamp` / `spaceClean` / `fixTimeStatus` | `*Ex` 能力位 |
| select ×3 | 场景、上下扫风位置、左右扫风位置 | `scene` / `portraitWindSet` / `orientationWindSet` | 左右扫风由 `leftType` 门控 |
| button ×2 | 电源切换、滤网复位 | `runStatus` / `filter` + `filterReset` | — |
| sensor ×16 | ~~回风温度~~（默认隐藏）、故障码、今日用电量/时长/费用、本月用电量/时长/费用、本年用电量/费用、制冷/制暖/抽湿记忆温度、定时计划、**逐时用电**、**设备信息** | 状态 bean + 电量/电价/模式温度/定时 + `ACGetAirconDayGraphInfo` / `ACGetAirconMonthGraphInfo` / `ACDevGetFwVersion` 等 | — |
| binary_sensor ×2 | 故障、~~滤网需更换~~（默认隐藏） | `alarmCode` / `filterReset` | — |
| number ×1 | **电价**（元/kWh，可写） | `ACGetAirconElectricChargeInfo` / `ACSetAirconElectricChargeInfo` | — |

### 默认隐藏的两个只读实体（2.3.1）

这两个都是**只读传感器，不是开关**，且不参与任何控制，隐藏不影响任何功能。原因是本机型的数据源无效：

| 实体 | 类型 | 实机值 | 判定 |
|---|---|---|---|
| 回风温度 | `sensor`（温度） | `inhaleTemperature = 128` | 官方哨兵值，本机不上报回风温度，实体恒 `unknown` |
| 滤网需更换 | `binary_sensor`（状态位） | `filterReset = 0` | 该字段是一次性**复位指令**而非到期状态位；官方 App 的滤网提醒由本地计时触发且仅 `airconType == 2` 弹出（本机为 0），实体恒 `off` |

实现方式为 `entity_registry_enabled_default = False`：全新安装不会注册这两个实体；已有安装需在 HA 实体注册表将这两条设为禁用（升级不会自动改动既有注册记录）。如需恢复，在 HA「实体」页面筛选「已禁用」并重新启用即可，`unique_id` / `entity_id` 均保留。

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

### 隐藏数据（2.3.0 新增）

把官方 H5 里定义、但 App 没在 HA 侧暴露的只读数据补齐。**不新增任何开关类实体**，绝大多数信息作为属性挂在已有实体上：

| 位置 | 来源端点 | 内容 |
|---|---|---|
| `sensor.…逐时用电` | `ACGetAirconDayGraphInfo` | state = 当前钟点用电量；属性 `hourly_power_kwh` / `hourly_cost_cny` / `hourly_set_temperature`（24 点数组）、`today_total_kwh`、`peak_hour` / `peak_kwh`；温度 `255` = 无读数 |
| `sensor.…设备信息` | `ACDevGetFwVersion` 等 6 个 | state = 固件版本（实机 `r_2_0_0_1616`）；属性 `ota_percent`、`device_name`、`master_user`、`device_count`、`help_links` / `error_links` / `problem_links`（官方帮助与故障排查图） |
| 记忆温度 3 个 sensor | `ACGetModeTempInfo`（原本就在轮询） | 新增 `wind_set` 属性（50 / 65 / 55），制冷另附 `nanoe_wind_set=65`，零额外请求 |
| `sensor.…本月用电量` | `ACGetAirconMonthGraphInfo` | 新增 `daily_power_kwh` / `daily_cost_cny`（30 天数组）属性 |
| `climate` | 状态 bean（原本就在轮询） | 新增 `device_diagnostics`（`airVersion` / `preAirconMode` / `runForbidden` / `unusualPresent` / `e017f` / 各 `*Type`）与 `capabilities`（全部 `*Ex` 能力位）属性 |

固件、OTA、帮助资料、设备名、主用户、全屋设备列表这 6 个端点变化极慢，在客户端缓存 **30 分钟**，不会让 60s 辅助轮询变成每轮十几个请求。逐时/逐日曲线与原有 7 个辅助端点一起按 60s 更新。

> 实测已失效、刻意不接：`ACGetAirconWeekGraphInfo` 恒返回 `8191 服务器内部错误`；`ACGetWeatherInfo` 所有省市返回空字段；`ACDevSetOTA` / `DevUnbind` 属危险写操作。`runForbidden` / `unusualPresent` 在官方 App 里**只读**（异常弹窗用），不做成开关。

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
- **增量写入（2.3.0）**：`ACDevSetStatusNewProtocol` 是增量协议，官方 H5 的 `setStatusInfoAWByOne` 只发单个字段（如 `{"params":{"portraitWindSet":65}}`），设备保留其余状态。实机回写当前值验证返回 `todoId:327/328/329` 且状态 diff 为空，因此集成不再全量回显状态 bean —— 少一次云端读取，也避免把只读诊断值误写回设备。旧 `CZ-RD501DW2` 的 `ACDevSetStatusInfoAW` 仍保留原来的 read-modify-write 白名单逻辑。官方 App 每条指令固定带 `buzzer=65`（提示音标记，非开关），集成同样处理。
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

2.3.0 新增「逐时用电」「设备信息」2 个只读 sensor（33→35），其余新数据全部作为属性挂到已有实体；同时把新协议控制改为增量写入、滤网复位改为 `filter` + `filterReset` 双发（官方 H5 用 `filter`，旧协议用 `filterReset`）。**所有现有 unique_id / entity_id 不变**，升级后新实体自动出现，无需重新配置。

2.3.1 把「回风温度」sensor 与「滤网需更换」binary_sensor 设为**默认禁用**（35 个定义 / 33 个默认可见），两者均为只读且在本机型上无有效数据；不删除定义、不改动 `unique_id`，可随时在 HA 中重新启用。已有安装需手动在实体注册表禁用这两条。

建议升级前备份 `/config/custom_components/panasonic_smart_china_zy`。本仓库保留了 `backup/v1.1.0` 分支与 `backup-v1.1.0-before-completion` 标签，可随时回滚。
