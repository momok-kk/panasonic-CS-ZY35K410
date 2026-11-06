# Panasonic CS-ZY35K410 for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/badge/version-2.5.0-blue.svg)]()

面向中国区「松下智能家电」App 的 Home Assistant 自定义集成，集成显示名 **Panasonic CS-ZY35K410**，**仅适配 CS-ZY35K410**（洵风系列，2024 AirconCommon 新协议，设备类别 `0900`）；2.4.0 起不再兼容其它机型或设备类别。域名 `panasonic_smart_china_zy`，不与原版 `panasonic_smart_china` 冲突。

## 协议依据

| 来源 | 说明 |
|---|---|
| `https://app.psmartcloud.com/ca/cn/0900/AirconCommon/` | 官方 H5 控制页，主包 `static/js/app.*.js` + **26 个懒加载 `chunk-*.js`** 才构成完整字段字典 |
| `ACDevGetStatusInfoAW` / `ACDevSetStatusNewProtocol` | 状态读取 / 控制端点 |
| 瀚思彼岸论坛 17153 帖 43# | `runStatus` 48/49、`runMode` 65–69、风速与扫风枚举的实测记录 |
| `panasonic_smart_china` v3.0.0 `profiles/split_ac_0900_airconcommon.py` | 同一协议的社区逆向成果，用于校验能力门控与用电统计端点 |
| **本机实机状态（2026-11-06）** | 温度刻度、`*Ex` 能力位、9 个辅助端点与 5 个元数据端点的返回结构均经真实响应核对 |

设备 token 由 `deviceId` 经双重 SHA-512 推导，已对本机实测值校验一致，**无需抓包，也无需反编译 APK**。

## 本次更新接入了什么（1.x → 2.4.0）

这一轮不是「多接几个实体」，而是拿官方 H5 主包 + 26 个懒加载 chunk 的完整字段字典，配合本机真实云端响应把协议重新对齐，最后在 2.4.0 收敛为单型号专用：**运行期覆盖 18 个云端端点（15 读 / 3 写），另有 2 个登录端点**；实体从字段错配、各自轮询，重整为 **6 个平台 / 32 个定义 / 30 个默认可见**；能拿到但不需要用户操作的数据一律做成属性。

### 新接入的云端能力

| 类别 | 端点 | 接入内容 | 频率 |
|---|---|---|---|
| 状态与控制 | `ACDevGetStatusInfoAW`、`ACDevSetStatusNewProtocol` | 开关 / 模式 / 设定温度 / 风速 / 上下与左右扫风 / 10 组 `*Ex` 门控开关 / 2 个按钮 | 15s 读，操作时写 |
| 用电统计 | `ACGetElectricChargeTodayInfo`、`ACGetElectricChargeDaylyInfo`、`ACGetAirconYearGraphInfo` | 今日 / 本月 / 本年电量、电费、运行时长 | 60s |
| **逐时·逐日曲线** | `ACGetAirconDayGraphInfo`、`ACGetAirconMonthGraphInfo` | 24 点 power / cost / 设定温度、30 天日用电与日费用数组（原本只在 App 图表里） | 60s |
| 电价与模式记忆 | `ACGetAirconElectricChargeInfo`、`ACSetAirconElectricChargeInfo`、`ACGetModeTempInfo` | 电价可写（本机 0.6 元/kWh）、制冷 / 制暖 / 抽湿记忆温度与风速 | 60s |
| 定时 | `ACGetAirconTimerNewProtocol`、`ACGetAirconFixTimeStatusInfo`、`ACSetAirconFixTimeStatusInfo` | 每周计划只读展示、定时总开关可写 | 60s |
| **设备元数据** | `ACDevGetFwVersion`、`ACDevGetOTAPercent`、`ACDevGetHelpAndErrorInfo`、`ACDevGetMasterUser`、`DevGetName` | 固件版本、OTA 进度、官方帮助 / 故障图、设备名、主用户 | 30min 客户端缓存 |
| 登录与认证 | `UsrGetBindDevInfo`、`UsrGetToken` | 绑定设备列表、token 推导、会话失效自动触发 HA 重新认证 | 配置 / reauth 时 |

`ACSetAirconTimerNewProtocol`（定时条目写入）虽已确认格式，但**刻意不调用**：误写会静默覆盖 App 里配好的计划。

### 落到 HA 的形式

- **实体**：32 个定义 / 30 个默认可见，原有 `unique_id` 与 `entity_id` 全部保留，旧自动化、仪表盘无需改动。清单见下节。
- **属性而非实体**：模式配色、19 个 `*Ex` 能力位、12 项设备诊断、24 点逐时曲线、30 天日曲线、记忆风速、官方帮助图链接，挂在 climate 与已有 sensor 上，不制造「实体多但没用」的噪音。
- **清理**：删掉 6 个协议里不存在的历史实体（`displaySet` / `sleepMode` / `powerfulMode` / `cleanMode` / `buzzer` / `selfcleanReset`）与 3 个本机型不支持的实体（UVC 除菌 / 语音提示 / 新风运行）；HA 侧清掉 16 条孤儿注册记录；「回风温度」「滤网需更换」2 个无效只读实体改为默认禁用（可随时重新启用）。
- **写入路径**：新协议改为增量写入（只发变更字段 + `buzzer=65`），滤网复位改为 `filter` + `filterReset` 双发；一次性指令不写入乐观状态，避免误报。
- **单型号收敛（2.4.0）**：删除第二套控制器 profile 与旧协议写入分支，配置流程仍完整（详见「单型号专用与配置流程」章节）。

### 实机校准后确定的行为（CS-ZY35K410，2026-11-06）

| 实机事实 | 结论 |
|---|---|
| `tempType=0`、`setTemperature=27` | 温度 x1 编码，`target_temp_step = 1.0`（26 → 27 → 28），**不是 0.5℃**；0.5℃ 只属于 `tempType=1` 的 x2 机型 |
| 51 个状态字段无实测室温，`inhaleTemperature=128` 是哨兵值 | 硬件有回风探头，但中国云端不下发读数（官方 App 同样读不到）；`climate.current_temperature` 走配置项 `sensor_entity_id`，当前接的是外部温感 `sensor.linp_ks2bb_ec09_temperature` |
| `lamp` 是反向二值（0=亮 / 1=灭），实机 `lamp=1` → HA 显示 `off` | **已实机确认状态正确**，保持 `switch` 平台，不换 `light`：无亮度 / 色温 / 颜色，换过去会被「全屋关灯」类自动化与语音指令误伤 |
| 51 个状态字段无 `scene`、也无 `sceneEx` | 本机型不支持「风感场景」（环抱/超远/怡静），2.5.0 已删除该 select；官方 App 有此功能，但只对特定 `airconType` 型号开放 |
| `spaceCleanEx=1` | 空间净化为硬件真实支持，保留 |
| `uvcEx=0` / `voiceSetEx=0` / `ervType=0` | UVC 除菌、语音提示、新风运行已移除 |

## 安装

HACS：添加本仓库为自定义仓库（类别 Integration）→ 搜索 `Panasonic CS-ZY35K410` → 下载 → 重启 HA。
手动：复制 `custom_components/panasonic_smart_china_zy` 到 `/config/custom_components/`，重启后添加集成。

集成在 HA 里的名称与图标由以下文件提供，全部为本地 PNG，不依赖在线资源：

| 文件 | 用途 |
|---|---|
| `brand/icon.png`（512×512） | 「添加集成」列表与集成卡片的方图 |
| `brand/logo.png`（1024×384） | 集成详情页顶部的横向 Logo |
| `icon.png` / `logo.png`（根目录） | 兼容 2024.11 之前旧版 HA 的读取路径 |

图标为 Panasonic 品牌蓝渐变底 + 白色壁挂机 + 三条送风曲线，浅色 / 深色主题下均可辨识。

> 松下账号是**单点登录**。HA 登录后手机 App 会掉线；手机重新登录又会让 HA 会话失效。会话失效时集成会提示「重新登录松下账号」，重新输入密码即可，设备 ID 与已有实体 ID 不变。

## 实体清单（共 32 个定义，默认启用 30 个）

| 平台 | 实体 | 状态字段 / 端点 | 门控 |
|---|---|---|---|
| climate ×1 | 空调 | `runStatus` / `runMode` / `setTemperature` / `windSet` / `portraitWindSet` / `orientationWindSet` | — |
| switch ×10 | 电源、强劲运转、自清洁、柔湿制冷、辅热、纳诺怡、睡眠、显示灯、空间净化、**定时开关** | `highCool` / `cleanSet` / `cool` / `elecHeat` / `nanoe` / `lamp` / `spaceClean` / `fixTimeStatus` | `*Ex` 能力位 |
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

> 上下 / 左右扫风只通过 climate 实体的「摆动模式」「水平摆动模式」两个下拉控制；2.5.0 已删除原来重复的 3 个 select（场景、上下扫风位置、左右扫风位置），`portraitWindSet` / `orientationWindSet` 仍由 climate 读写。

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
| `sensor.…设备信息` | `ACDevGetFwVersion` 等 5 个 | state = 固件版本（实机 `r_2_0_0_1616`）；属性 `ota_percent`、`device_name`、`master_user`、`help_links` / `error_links` / `problem_links`（官方帮助与故障排查图） |
| 记忆温度 3 个 sensor | `ACGetModeTempInfo`（原本就在轮询） | 新增 `wind_set` 属性（50 / 65 / 55），制冷另附 `nanoe_wind_set=65`，零额外请求 |
| `sensor.…本月用电量` | `ACGetAirconMonthGraphInfo` | 新增 `daily_power_kwh` / `daily_cost_cny`（30 天数组）属性 |
| `climate` | 状态 bean（原本就在轮询） | 新增 `device_diagnostics`（`airVersion` / `preAirconMode` / `runForbidden` / `unusualPresent` / `e017f` / 各 `*Type`）与 `capabilities`（全部 `*Ex` 能力位）属性 |

固件、OTA、帮助资料、设备名、主用户这 5 个端点变化极慢，在客户端缓存 **30 分钟**，不会让 60s 辅助轮询变成每轮十几个请求。逐时/逐日曲线与原有 7 个辅助端点一起按 60s 更新。

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
- **增量写入（2.3.0）**：`ACDevSetStatusNewProtocol` 是增量协议，官方 H5 的 `setStatusInfoAWByOne` 只发单个字段（如 `{"params":{"portraitWindSet":65}}`），设备保留其余状态。实机回写当前值验证返回 `todoId:327/328/329` 且状态 diff 为空，因此集成不再全量回显状态 bean —— 少一次云端读取，也避免把只读诊断值误写回设备。2.4.0 起旧协议的 read-modify-write 分支与写入白名单已整体删除。官方 App 每条指令固定带 `buzzer=65`（提示音标记，非开关），集成同样处理。
- **认证失效**：识别顶层 `errorCode` 与嵌套 `error.code`（3003/3004/403/4102），触发 HA 重新认证流程，不再静默失败。
- **温度刻度**：实机 `tempType=0` / `setTemperature=27` 对应 27℃，本机为 **x1、步长 1.0℃**；集成仍保留自动判断（>45 视为 x2）以兼容 `tempType=1` 的半度机型。云端不下发实测室温，`current_temperature` 由配置项 `sensor_entity_id` 指定的外部温感提供。
- **设备归组**：所有实体带 `DeviceInfo`，在 HA 中归入同一个设备卡片。
- **单型号**：`DEVICE_PROFILE` 是唯一的设备描述；实体平台仍以数据驱动方式读取它，但没有任何型号探测、回退或第二套协议分支。

## 单型号专用与配置流程（2.4.0）

本集成现在**只接 CS-ZY35K410**（`deviceId` 类别 `0900`）。删除的代码：

| 已删除 | 原用途 |
|---|---|
| `CZ-RD501DW2` 完整 profile | 另一套线控器的模式 / 风速 / 摆风映射与 7 个英文实体 |
| `ACDevSetStatusInfoAW` 旧写端点、`_send_command_legacy`、写入白名单 `SAFE_KEYS` / `AIRCONCOMMON_SAFE_KEYS` | 旧机型的 read-modify-write 全量回显 |
| 配置表单的「线控器/遥控器型号」下拉与型号自动探测 | 多机型选择 |
| `FAN_MUTE`（Quiet）与 `fan_payload_overrides` 分支 | 旧机型静音档，本机映射为空，属死代码 |
| `ACGetAllAirconListCommon` 与 `device_count` 属性 | 拉取账号下全部空调列表 |

**配置流程一步未砍**，仍是完整三步 + 重新认证：

1. **登录**：`UsrGetToken` → `UsrLogin` → `UsrGetBindDevInfo`；会话（usrId / SSID / familyId）写入 `hass.data` 缓存，重复配置时先验证缓存会话是否有效。
2. **设备选择**：设备列表只保留类别 `0900` 的空调（洗衣机等其它设备不再出现）；表单保留「选择空调设备」与「关联室温传感器（可选）」，已配置设备自动排除，`no_devices_found` / `all_devices_configured` / `token_generation_failed` 三种异常分支齐全。
3. **创建条目**：由 `deviceId` 按双重 SHA-512 推导 token，写入 usrId / SSID / deviceId / token / 可选温感；型号由代码固定，不再需要用户选择。
4. **重新认证**：云端返回 4102 / 3003 等认证错误时进入 reauth，只刷新 usrId 与 SSID，**设备 ID 与全部实体 ID 不变**。

> 旧配置条目数据里残留的 `controller_model` 键会被忽略，不影响加载；所有 `unique_id` / `entity_id` 保持不变。

## 已知限制

| 项目 | 状态 |
|---|---|
| 其它机型 / 设备类别 | **2.4.0 起不支持**：只接 CS-ZY35K410（0900），旧线控器 CZ-RD501DW2 与非空调设备已从代码中移除 |
| 空调本体室温 | 云端不下发（`inhaleTemperature=128` 为哨兵值，官方 App 也读不到）；需外部温感 + 配置项 `sensor_entity_id` |
| 风感场景（环抱/超远/怡静） | **本机型不支持**：51 个状态字段无 `scene`，也无 `sceneEx` 能力位 → 2.5.0 已删除该 select（原实体恒为 `unavailable`） |
| 显示灯平台 | 保持 `switch`（协议为反向二值 0=亮 / 1=灭，已实机确认）；无亮度 / 色温，不转成 `light` |
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

2.4.0 收敛为单型号专用：删除 CZ-RD501DW2 profile / 旧协议写入 / 型号下拉 / 全屋设备列表端点（`device_count` 属性随之移除）。**配置流程仍完整**（登录 → 设备发现与选择 → token → reauth），保留注册表升级时所有 `unique_id` / `entity_id` 不变，无需重新配置；旧条目里的 `controller_model` 键被忽略。

2.4.1 集成显示名改为 `Panasonic CS-ZY35K410`（manifest `name`），并补齐品牌图标：`brand/icon.png`、`brand/logo.png` 及根目录同名文件。**只影响集成在 UI 中的名称与图标**，设备名、`unique_id`、`entity_id` 与实体状态均不变。

2.5.0 删除 `select` 平台（35→32，平台数 7→6）：① `场景`——官方 App 有「风感场景」（关闭/怡静风/超远风/环抱风，64–67），但本机状态报文里既无 `scene` 字段也无 `sceneEx` 能力位，实体永远 `unavailable`（灰）；② `上下扫风位置`、`左右扫风位置`——与 climate 的「摆动模式」「水平摆动模式」写的是同一对字段（`portraitWindSet` / `orientationWindSet`），重复入口。扫风统一由 climate 实体控制，功能无损失。三个 select 在 HA 中会变成孤儿实体，需在「实体」页面删除（本次已代为清理注册表）。

> 关于 `entity_id`：2.4.0 说的「不变」适用于保留实体注册表的升级；若清空注册表做全新安装，HA 会按当前中文实体名重新生成 ID（如 `switch.wo_shi_kong_diao_dian_yuan`），`unique_id` 与实体功能不受影响。

建议升级前备份 `/config/custom_components/panasonic_smart_china_zy`。本仓库保留了 `backup/v1.1.0` 分支与 `backup-v1.1.0-before-completion` 标签，可随时回滚。
