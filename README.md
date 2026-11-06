# Panasonic Smart China ZY Custom for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/badge/version-2.0.0-blue.svg)]()

面向中国区「松下智能家电」App 的 Home Assistant 自定义集成，重点适配 **CS-ZY35K410**（洵风系列，2024 AirconCommon 新协议）。域名 `panasonic_smart_china_zy`，不与原版 `panasonic_smart_china` 冲突。

## 协议依据

| 来源 | 说明 |
|---|---|
| `https://app.psmartcloud.com/ca/cn/0900/AirconCommon/` | 官方 H5 控制页，`static/js/app.*.js` 含完整字段、枚举与 `*Ex` 能力位 |
| `ACDevGetStatusInfoAW` / `ACDevSetStatusNewProtocol` | 状态读取 / 控制端点 |
| 瀚思彼岸论坛 17153 帖 43# | `runStatus` 48/49、`runMode` 66/67/68、风速与扫风枚举的实测记录 |
| `panasonic_smart_china` v3.0.0 `profiles/split_ac_0900_airconcommon.py` | 同一协议的社区逆向成果，用于校验能力门控与用电统计端点 |

设备 token 由 `deviceId` 经双重 SHA-512 推导，已对本机实测值校验一致，**无需抓包**。

## 安装

HACS：添加本仓库为自定义仓库（类别 Integration）→ 搜索 `Panasonic Smart China ZY Custom` → 下载 → 重启 HA。
手动：复制 `custom_components/panasonic_smart_china_zy` 到 `/config/custom_components/`，重启后添加集成。

> 松下账号是**单点登录**。HA 登录后手机 App 会掉线；手机重新登录又会让 HA 会话失效。会话失效时集成会提示「重新登录松下账号」，重新输入密码即可，设备 ID 与已有实体 ID 不变。

## 实体清单

| 平台 | 实体 | 状态字段 | 门控 |
|---|---|---|---|
| climate | 空调 | `runStatus` / `runMode` / `setTemperature` / `windSet` / `portraitWindSet` / `orientationWindSet` | — |
| switch ×12 | 电源、强劲制冷、自清洁、柔湿制冷、辅热、纳诺怡、睡眠、显示灯、空间净化、蜂鸣、UVC 除菌、语音提示 | `highCool` / `cleanSet` / `cool` / `elecHeat` / `nanoe` / `lamp` / `spaceClean` / `uvc` / `voiceSet` 等 | `*Ex` 能力位 |
| select ×7 | 场景、上下扫风位置、左右扫风位置、显示灯模式、睡眠/强劲/清洁模式 | `scene` / `portraitWindSet` / `orientationWindSet` 等 | 左右扫风由 `leftType` 门控 |
| button ×3 | 电源切换、滤网复位、自清洁复位 | `runStatus` / `filterReset` / `selfcleanReset` | — |
| sensor ×9 | 回风温度、故障码、今日用电量/运行时长/费用、本月用电量/运行时长/费用、本年用电量 | 状态 bean + `ACGetElectricChargeTodayInfo` / `ACGetElectricChargeDaylyInfo` / `ACGetAirconYearGraphInfo` | — |
| binary_sensor ×3 | 故障、滤网需更换、新风运行 | `alarmCode` / `filterReset` / `ervMode` / `ervCheck` | — |

合计 35 个实体。能力位为 0 或状态里不存在该字段时，实体显示为「不可用」，这是硬件不支持的正常表现，可在 HA 里手动禁用。

### climate 可用值

- 模式：自动(65)、制冷(66)、制热(67)、除湿(68)、送风(69)、关机
- 风速：Auto(65)、Min(49)、Low(50)、Medium(52)、High(54)、Max(55)，对应 App 的自动/20%/40%/60%/80%/100%
- 上下扫风：Auto(70)、方向 1–5(65/68/67/69/66)
- 左右扫风：Auto(64)、最左(66)、偏左(108)、正对(67)、偏右(87)、最右(65)
- 场景：关闭(64)、怡静风(65)、超远风(66)、环抱风(67)

## 架构

- **单设备单轮询**：所有实体共享一个 `PanasonicStatusCoordinator`（15s）与一个 `PanasonicAuxCoordinator`（60s），不再每个实体各发一次云端请求。
- **Read-Modify-Write**：控制前重新读取最新状态，只写 `AIRCONCOMMON_SAFE_KEYS` 中的 18 个可写字段；显式指令（复位、场景等）单独透传，避免把只读值回写。
- **认证失效**：识别顶层 `errorCode` 与嵌套 `error.code`（3003/3004/403/4102），触发 HA 重新认证流程，不再静默失败。
- **温度刻度自适应**：社区对 `setTemperature` 是 x1 还是 x2 有分歧，集成按实时值自动判断（>45 视为 x2），读写一致。
- **设备归组**：所有实体带 `DeviceInfo`，在 HA 中归入同一个设备卡片。

## 已知限制

| 项目 | 状态 |
|---|---|
| 定时开关机（number） | 已定位 `ACGet/SetAirconTimerNewProtocol` 端点，但缺少实机返回样例，未实现，避免臆造字段 |
| 新风独立 fan 实体 | `ervMode` / `ervWind` 已用于「新风运行」二值传感器，未额外做 fan 平台 |
| 旧协议字段 select | `sleepMode` / `powerfulMode` / `cleanMode` 沿用历史配置；若设备不上报则显示不可用 |
| 单点登录 | 无法规避，需通过重新认证刷新 SSID |
| 云端自签名证书 | 请求使用 `ssl=False`；如 HA 环境限制，请检查网络策略 |

## 升级说明

从 1.1.0 / 1.2.1 升级到 2.0.0 时，**域名、设备 ID、全部 unique_id 均保持不变**，现有自动化与仪表盘无需改动。新增实体会自动出现；能力不支持的实体显示为不可用。

建议升级前备份 `/config/custom_components/panasonic_smart_china_zy`。本仓库保留了 `backup/v1.1.0` 分支与 `backup-v1.1.0-before-completion` 标签，可随时回滚。
