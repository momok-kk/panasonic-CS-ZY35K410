# 松下 CS-ZY35K410 专用集成

[![release](https://img.shields.io/github/v/release/609293964/panasonic-CS-ZY35K410?display_name=tag&sort=semver)](https://github.com/609293964/panasonic-CS-ZY35K410/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.8%2B-41BDF5.svg)]()
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=609293964&repository=panasonic-CS-ZY35K410&category=integration)

非官方 Home Assistant 集成，通过松下中国智能家电云（`app.psmartcloud.com`）接入 **CS-ZY35K410** 壁挂空调。

**只支持这一个型号** CS-ZY35K410` 这一种设备，多设备账号下其余空调不会出现在选择列表里。

**34 个实体（默认启用 30 个）**，支持：完整空调控制、电量与电费统计、逐时用电曲线、指示灯与纳诺怡等九路功能开关、定时计划、故障诊断，并**自带开箱即用的空调控制卡片**。


## 自带空调卡片（开箱即用）

集成附带 `custom:panasonic-climate-card`，安装并重启 HA 后无需任何额外配置：

## 功能

### 空调控制

- **模式**：自动 / 制冷 / 制暖 / 抽湿 / 送风
- **温度**：16–30 ℃，步长 1.0 ℃（本机 `tempType=0`）
- **风速**：6 档（自动 / 最小 / 低 / 中 / 高 / 最大）
- **扫风**：上下 6 档（Auto、Up、Up Middle、Middle、Down Middle、Down）、左右 6 档（Auto、Left、Left Middle、Center、Right Middle、Right）
- **按钮**：电源切换、滤网复位
- **电价**：元/kWh，可直接在 HA 里改并写回云端，云端据此计算费用

### 电量统计
- 电量为 `total_increasing`，可直接进 HA 能源面板

## 实体清单（34 个定义，默认启用 30 个）

| 平台 | 数量 | 实体 |
|---|---|---|
| `climate` | 1 | 空调 |
| `switch` | 10 | 电源、强劲运转、自清洁、柔湿制冷、辅热、纳诺怡、睡眠、显示灯、空间净化、定时开关 |
| `sensor` | 16 | 故障码、今日用电量 / 时长 / 费用、本月用电量 / 时长 / 费用、本年用电量 / 费用、制冷 / 制暖 / 抽湿记忆温度、定时计划、逐时用电、设备信息、~~回风温度~~ |
| `binary_sensor` | 2 | 故障、~~滤网需更换~~ |
| `button` | 2 | 电源切换、滤网复位 |
| `number` | 1 | 电价 |
| `select` | 2 | ~~上下扫风位置~~、~~左右扫风位置~~ |

### 方式一：HACS 一键添加（推荐）

点了下面这个按钮会直接跳到**你自己的** Home Assistant，弹出「添加自定义存储库」并预填好地址，确认后安装即可：

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=609293964&repository=panasonic-CS-ZY35K410&category=integration)

前提：HA 里已装 HACS，且浏览器能访问到你的 HA（`my.home-assistant.io` 是官方跳板，不会上传任何数据）。

### 方式二：HACS 手动添加

1. HACS → 右上角 **⋮** → **自定义存储库 / Custom repositories**
2. 地址填 `https://github.com/609293964/panasonic-CS-ZY35K410`，类别选 **集成 / Integration** → 添加
3. 回到 HACS 搜索 `Panasonic CS-ZY35K410` → 下载
4. **重启 Home Assistant**（custom component 必须重启才加载）

### 方式三：手动复制

下载仓库 ZIP，把 `custom_components/panasonic_smart_china_zy` 整个目录放到 `/config/custom_components/`，重启 HA。

> 目录名必须是 `panasonic_smart_china_zy`（与 `manifest.json` 的 `domain` 一致），改名会导致集成加载失败。

## 配置

1. 设置 → 设备与服务 → 添加集成 → 搜索 `Panasonic CS-ZY35K410`
2. 输入松下智能家电 App 的**手机号 / 邮箱 + 密码**（与官方 App 同一账号）
3. 集成自动拉取设备列表，只显示本型号；选中后自动推导 token 并创建条目

> 松下账号是**单点登录**：HA 登录后手机 App 会掉线，手机重新登录又会让 HA 会话失


## 说明

- 本项目与松下无关联，仅供自用与学习
- 仓库未附许可证文件，如需分发请自行补充
