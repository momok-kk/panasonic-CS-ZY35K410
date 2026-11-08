# 松下 CS-ZY35K410 专用集成

[![release](https://img.shields.io/github/v/release/609293964/panasonic-CS-ZY35K410?display_name=tag&sort=semver)](https://github.com/609293964/panasonic-CS-ZY35K410/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.8%2B-41BDF5.svg)]()
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=609293964&repository=panasonic-CS-ZY35K410&category=integration)

非官方 Home Assistant 集成，通过松下中国智能家电云（`app.psmartcloud.com`）接入 **CS-ZY35K410** 壁挂空调。

**只支持这一个型号**——代码里没有其它机型、控制器或旧协议的兼容分支，配置时也只认 `0900 / CS-ZY35K410` 这一种设备，多设备账号下其余空调不会出现在选择列表里。

**34 个实体（默认启用 30 个）**，支持：完整空调控制、电量与电费统计、逐时用电曲线、指示灯与纳诺怡等九路功能开关、定时计划、故障诊断，并**自带开箱即用的空调控制卡片**。

## 界面

控制面板：设备信息、电价、电源与各项功能开关。

![控制面板](docs/images/panel-control.png)

传感器：用电量 / 费用 / 运行时长、记忆温度、定时计划、故障与设备信息。

![传感器](docs/images/panel-sensors.png)

## 自带空调卡片（开箱即用）

集成附带 `custom:panasonic-climate-card`，安装并重启 HA 后无需任何额外配置：

- 卡片 JS 与 `panasonic:nanoe` 图标集由集成注册静态路径并注入前端，**不用复制 `/config/www`、不用 `lovelace.resources`、不用手动加缓存版本号**。
- UI 仪表盘：添加卡片 → 搜索「松下 CS-ZY35K410 空调」；YAML 仪表盘：写一行 `type: custom:panasonic-climate-card` 即可。
- **不写死任何 entity_id**：集成在 climate 实体的 `panasonic_entities` 属性里发布「功能 key → entity_id」映射（按 config entry 隔离），卡片按 key 解析开关、传感器与按钮。用户在松下 App 里怎么命名、装几台都不影响。
- **多台同型号**：卡片自动列出所有本集成的 climate 实体，顶部出现设备下拉框可切换；也可用 `entity:` 固定其中一台。
- 可选配置：`name`、`step`、`temp_entity`、`show_charts`、`nanoe_logo`；`switches` / `cost_main` / `cost_extra` 可用带 `id` 的数组覆盖，指向任意 HA 实体。
- 少数功能 key 会跨平台重名（`runStatus` 既是电源开关又是电源切换按钮）：短键取可交互的 `switch`，另提供 `runStatus__switch` / `runStatus__button` 精确键，映射不会丢实体。
- 若以前手动注册过 `/local/panasonic-climate-card.js`，请删除那条资源并强制刷新浏览器，避免旧版抢占元素注册。

## 功能

### 空调控制

- **模式**：自动 / 制冷 / 制暖 / 抽湿 / 送风
- **温度**：16–30 ℃，步长 1.0 ℃（本机 `tempType=0`）
- **风速**：6 档（自动 / 最小 / 低 / 中 / 高 / 最大）
- **扫风**：上下 6 档（Auto、Up、Up Middle、Middle、Down Middle、Down）、左右 6 档（Auto、Left、Left Middle、Center、Right Middle、Right）
- **按钮**：电源切换、滤网复位
- **电价**：元/kWh，可直接在 HA 里改并写回云端，云端据此计算费用

### 电量统计

- 今日 / 本月 / 本年：用电量（kWh）、费用（¥）、运行时长（分钟）
- 费用实体使用 `total_increasing`（不带 `MONETARY` 设备类，因为 HA 只允许它配 `total`）：跨天 / 跨月归零按新计量周期处理，长期统计不再产生负增量
- **逐时用电**：24 点数组放在实体属性 `hourly_power_kwh`，适合 apexcharts 等自定义卡片画曲线（该实体不带 `state_class`，不生成长期统计）
- 本月每日电量与费用、30 天曲线、记忆风速等明细，作为属性挂在对应实体上，不额外占用实体
- 电量为 `total_increasing`，可直接进 HA 能源面板

### 功能开关（均由 `*Ex` 能力位门控）

强劲运转、自清洁、柔湿制冷、辅热、纳诺怡、睡眠、**显示灯**、空间净化、**定时开关**。

- 显示灯为反向字段（`lamp=0` 表示灯亮），集成已做反转，实体 `on` 就是灯亮
- 定时开关控制云端「定时计划」是否生效；计划内容本身只读（见已知限制）

### 诊断与信息

- **故障**（二进制传感器）+ **故障码**：`0000` 正常、`07DF` 碰撞开关异常、`OFFLINE` 本体离线
- **定时计划**：显示已配置的组数（如 8），完整周计划作为属性
- **设备信息**：固件版本（如 `r_2_0_0_1616`），另有 OTA 进度、主账号、帮助错误信息等属性
- **记忆温度**：制冷 / 制暖 / 抽湿三个模式各自记住的设定温度

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

划线项默认禁用（`disabled_by: integration`），需要时在「设置 → 设备与服务 → 实体 → 筛选已禁用」里手动启用，位置数据是现成的，启用即有值：

- **回风温度**：本机 `inhaleTemperature` 恒为哨兵值 `128`，没有真实回风温度可报
- **滤网需更换**：`filterReset` 在协议里是一次性复位指令而非状态位，本机 `airconType=0` 也不会触发 App 的滤网提醒
- **上下 / 左右扫风位置**：与空调卡的两个摆动下拉写同一对字段，属重复入口，保留作备用

### 实体 ID 命名与多设备

全新安装时实体 ID 统一为 `ZY35K410_<功能 key>`（如 `climate.zy35k410`、`switch.zy35k410_nanoe`、`sensor.zy35k410_cost_today`），由 `suggested_object_id` 生成，**与松下 App 里的设备名无关**；显示名称仍沿用 App 名称。第二台同型号空调由 HA 自动加数字后缀（如 `switch.zy35k410_nanoe_2`）。

> **升级不会改名**：已存在的实体注册项保留原 `entity_id`，升级到 2.7.0 不会改变任何自动化或历史。只有删除集成条目后重新添加（全新安装）才会生成新命名。卡片通过 `panasonic_entities` 映射工作，两种命名都能用。

## 实体图标

34 个实体全部显式指定图标，不再回退到「所有开关都长一样」的 HA 默认字形。除纳诺怡使用集成自带图标集外，图标名取自 Material Design Icons 7.4.47，已逐个校验存在。

| 类别 | 图标 |
|---|---|
| 空调主机 | `mdi:air-conditioner` |
| 电源 / 电源切换 | `mdi:power` / `mdi:power-cycle` |
| 强劲运转 | `mdi:fan-plus` |
| 自清洁 | `mdi:shimmer` |
| 柔湿制冷 / 辅热 | `mdi:water-percent` / `mdi:heat-wave` |
| 睡眠 | `mdi:sleep` |
| 显示灯 | `mdi:led-on` |
| 空间净化 / 滤网复位 | `mdi:air-purifier` / `mdi:air-filter` |
| 定时开关 / 定时计划 | `mdi:timer-outline` / `mdi:calendar-clock` |
| 用电量 / 费用 / 运行时长 | `mdi:flash` / `mdi:currency-cny` / `mdi:clock-outline` |
| 逐时用电 / 设备信息 | `mdi:chart-timeline-variant` / `mdi:information-outline` |
| 故障 / 故障码 | `mdi:alert-circle` / `mdi:alert-circle-outline` |
| 记忆温度（制冷 / 制暖 / 抽湿） | `mdi:snowflake` / `mdi:fire` / `mdi:water-percent` |
| 上下 / 左右扫风位置 | `mdi:arrow-up-down` / `mdi:arrow-left-right` |
| 纳诺怡 | `panasonic:nanoe`（集成自带图标集） |

### 纳诺怡：`panasonic:nanoe`

MDI 共 7447 个图标，**没有 `nanoe`**（连别名与标签都没有），所以图标选择器里搜到的同名项没有路径，选中后是一片空白——那不是一个可用的 MDI 图标。因此按官方 App 资源重绘了这个标记：右缘被竖直切平的大圆加右侧小圆点。

![nanoe](custom_components/panasonic_smart_china_zy/brand/nanoe.png)

集成把它注册成真正的图标集，纳诺怡开关的**默认图标就是 `panasonic:nanoe`**（2.6.3 起）：

- 由 `frontend/panasonic_icons.js` 通过 `window.customIcons` 注册 `panasonic:` 前缀，`__init__.py` 在集成启动时注册静态路径并以带版本号的 URL 注入前端，无需手动添加资源；
- 不再使用 `entity_picture` / 内嵌 data URI，HA 原生卡片与第三方卡片（Mushroom、button-card 等）显示同一图标；
- 在任意图标选择器里搜索 `nanoe`、`纳诺怡`、`panasonic` 都能列出并正常渲染，也可用于其它实体、卡片、自动化；
- 44×44 画布留白后，大圆在 36px 图标位里约 18px，与相邻的 24px MDI 图标视觉重量一致；
- 填充跟随主题色（`currentColor`），深色主题下比固定深蓝 `#2C4198` 更清晰；`brand/nanoe.svg` / `brand/nanoe.png` 保留深蓝原图，可复制到 `/config/www/` 供自定义卡片使用。

技术背景：HA 前端对非 MDI 前缀的图标，若 `window.customIcons` 中没有对应图标集，会退回已在现代前端中移除的 `<iron-icon>`，表现即为空白。图标集以合并方式注册（不覆盖其它集成已有的同名前缀）；也正因为图标由集成注入前端，**卸载或停用集成后 `panasonic:` 前缀失效**，已手动选用该图标的地方会显示空白。

## 安装

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

安装完成后，集成名称与图标全部为本地资源，不依赖在线 CDN：`brand/icon.png`（512×512，集成列表方图）、`brand/logo.png`（1024×384，详情页横幅）、`brand/nanoe.svg` + `brand/nanoe.png`（纳诺怡标记原图，仅供参考）、`frontend/panasonic_icons.js`（图标集）、`frontend/panasonic-climate-card.js`（自带空调卡片），根目录同名文件用于兼容 2024.11 之前的 HA。

## 配置

1. 设置 → 设备与服务 → 添加集成 → 搜索 `Panasonic CS-ZY35K410`
2. 输入松下智能家电 App 的**手机号 / 邮箱 + 密码**（与官方 App 同一账号）
3. 集成自动拉取设备列表，只显示本型号；选中后自动推导 token 并创建条目

> 松下账号是**单点登录**：HA 登录后手机 App 会掉线，手机重新登录又会让 HA 会话失效。会话过期时 HA 会提示「重新登录松下账号」，重新输密码即可，设备 ID 与已有实体 ID 都不变。

## 已知限制

| 项 | 说明 |
|---|---|
| 风感场景（怡静 / 超远 / 环抱） | **本机型不支持**：状态报文无 `scene` 字段、无 `sceneEx` 能力位 |
| 定时计划编辑 | 只读。写入需要 `ACSetAirconTimerNewProtocol` 并按能力位裁剪字段，写错会静默改掉 App 里的日程，故不开放 |
| 回风温度 | 本机不上报，恒为哨兵 `128` |
| 滤网提醒 | 本机 `airconType=0`，无有效状态位 |
| 摆动档位显示英文 | HA 前端只翻译内置值（off / vertical / horizontal / both），自定义档位原样显示；改成中文会改变 state 值，影响历史与自动化 |
| 定时计划星期编码 | 按 `weekList[].week` 显式字段映射（假定 1=周一…7=周日），不再依赖数组下标；属性里保留 `week_raw` / `week_source` 供与 App 日程核对 |
| 温度步长 | 固定 1.0 ℃。协议 `tempType=1` 才支持 0.5 ℃，本机为 0 |

## 数据来源

状态与控制走 `ACDevGetStatusInfoAW` / `ACDevSetStatusNewProtocol`（单字段增量写入，不覆盖其它参数）；另有电量、电价、模式温度、定时、固件等只读端点。所有字段语义均对照官方 AirconCommon H5 包并在实机（2026-11-06）校准，非官方文档。云端接口变更可能导致集成失效，届时需跟随官方 App 更新。写命令成功后立即乐观更新，并在 2 秒内合并回读一次云端状态（连续操作只回读一次）；会话过期时服务调用会直接报错并触发重新认证。

## 说明

- 本项目与松下无关联，仅供自用与学习
- 仓库未附许可证文件，如需分发请自行补充
