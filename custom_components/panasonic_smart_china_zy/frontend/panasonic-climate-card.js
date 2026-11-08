/**
 * 松下 CS-ZY35K410 空调卡片 · 集成自带，开箱即用。
 *
 * 本文件随集成一起分发，由 __init__.py 注册静态路径并以 extra JS URL 注入
 * HA 前端；无需复制到 /config/www，也无需 lovelace.resources 条目。
 * YAML / UI 仪表盘都只要写 `type: custom:panasonic-climate-card`。
 *
 * 实体发现（关键）：不写死任何 entity_id。集成在 climate 实体的
 * `panasonic_entities` 属性里发布「功能 key → entity_id」映射（按 config
 * entry 隔离），卡片按 key 解析；同时扫描所有带该属性的 climate 实体实现
 * 自动发现。用户在松下 App 里给空调起什么名字、装几台同型号都不影响。
 * 多台设备时卡片顶部出现下拉框，可直接切换。
 *
 * 用户仍可在卡片配置里传 entity / name / switches / cost_main / cost_extra
 * 显式覆盖；switches 等数组元素可带 `id` 指向任意 HA 实体。
 *
 * 其余行为：温度步进 / 上下限 / 模式 / 风速 / 摆风档位全读 climate 属性；
 *   24h 温度曲线取 recorder 历史；实体缺失即隐藏；传感器无效值显示「—」。
 * 状态位：nanoe_logo 图片 > panasonic:nanoe 图标集 > 内置矢量降级。
 * 外观：霜白一套，变量集中在 THEME。
 */

const MODES = [
  { v: 'auto', t: '自动' },
  { v: 'cool', t: '制冷' },
  { v: 'dry', t: '除湿' },
  { v: 'heat', t: '制热' },
  { v: 'fan_only', t: '送风' },
];

// 显示用中文映射。键必须与实体 attributes 里的原始值完全一致；
// 未收录的值原样显示，避免集成升级后出现空白或错误标签。
const LABELS = {
  fan: {
    auto: '自动', Min: '最小', low: '低速', medium: '中速', high: '高速', Max: '超强',
  },
  swingV: {
    Auto: '自动', Up: '向上', 'Up Middle': '偏上', Middle: '中间',
    'Down Middle': '偏下', Down: '向下',
  },
  swingH: {
    Auto: '自动', Left: '最左', 'Left Middle': '偏左', Center: '正对',
    'Right Middle': '偏右', Right: '最右',
  },
};

// 功能清单只描述集成的「实体 key」，运行时从 climate 实体的
// panasonic_entities 属性解析成真实 entity_id，因此与设备命名无关。
// 用户可用卡片配置里的同名数组覆盖，元素带 `id` 即可指向任意 HA 实体。
const PINNED = [
  { key: 'lamp', label: '显示灯', kind: 'light' },
  { key: 'nanoe', label: '纳诺怡', kind: 'nanoe' },
];

// 主卡常驻的费用传感器读数；实体不存在即隐藏。
const COST_MAIN = [
  { key: 'cost_month', label: '本月费用', cost: true },
  { key: 'cost_today', label: '今日费用', cost: true },
];

// 其余费用与用电明细，收进「更多」抽屉；实体不存在即隐藏，不占位。
const COST_EXTRA = [
  { key: 'cost_year', label: '本年费用', cost: true },
  { key: 'energy_today', label: '今日用电量' },
  { key: 'duration_today', label: '今日运行时长' },
  { key: 'energy_month', label: '本月用电量' },
  { key: 'duration_month', label: '本月运行时长' },
  { key: 'energy_year', label: '本年用电量' },
  { key: 'hourly_energy', label: '逐时用电' },
  { key: 'electricity_charge', label: '电价' },
];

// 唯一外观：霜白。v 里的键会转成 CSS 变量 --pc-<key>（驼峰转连字符）。
const THEME = {
  name: '霜白',
  v: {
    card: '#FFFFFF', text: '#1D1D1F', sub: '#5B7899', muted: '#86868B',
    faint: '#A1A1A6', inactive: '#6E6E73', surface: '#F5F5F7', raised: '#FFFFFF',
    tile: '#F5F5F7', more: '#E8F2FD', label: '#86868B', value: '#1D1D1F',
    power: '#FFFFFF', placeholder: '#D2D2D7', overlay: 'rgba(29,29,31,.28)',
    line: '#E8E8ED', sheet: '#FFFFFF', radius: '28px', tileRadius: '16px',
    border: '1px solid transparent', tileBorder: '1px solid transparent',
    activeBorder: '1px solid transparent', moreBorder: '1px solid transparent',
    shadow: '0 12px 40px rgba(0,0,0,.06)', segShadow: '0 2px 6px rgba(0,0,0,.08)',
    sheetShadow: '0 -12px 40px rgba(0,0,0,.10)', powerShadow: '0 2px 10px rgba(0,0,0,.06)',
    lightOn: '#34C759', nanoeOn: '#2C4198', nanoeGlow: 'rgba(44,65,152,.30)', indicatorOff: '#C7C7CC',
    chartTemp: '#0071E3', energy: '#FF9F0A', pinBg: 'rgba(255,255,255,.62)',
  },
  accents: {
    cool: '#0071E3', heat: '#E8791B', dry: '#5B7FB5',
    fan_only: '#6E6E73', auto: '#2E9E63', off: '#86868B',
  },
  gradients: {
    cool: 'linear-gradient(180deg,#E6F2FF 0%,#CFE6FF 100%)',
    heat: 'linear-gradient(180deg,#FFF1E4 0%,#FFD8B2 100%)',
    dry: 'linear-gradient(180deg,#EDF3FF 0%,#DCE7FA 100%)',
    fan_only: 'linear-gradient(180deg,#F2F2F7 0%,#E5E5EA 100%)',
    auto: 'linear-gradient(180deg,#E9F6EF 0%,#D5EDDF 100%)',
    off: 'linear-gradient(180deg,#F5F5F7 0%,#E8E8ED 100%)',
  },
};

// 默认开关 / 只读信息 / 动作按钮清单，同样只写 key。
const SWITCHES = [
  { key: 'nanoe', label: '纳诺怡' },
  { key: 'spaceClean', label: '空间净化' },
  { key: 'powerful', label: '强劲运转' },
  { key: 'cool', label: '柔湿制冷' },
  { key: 'sleep', label: '睡眠曲线' },
  { key: 'elecHeat', label: '电辅热' },
  { key: 'lamp', label: '显示灯' },
  { key: 'selfClean', label: '自清洁' },
  { key: 'fix_time_status', label: '定时开关' },
];

const INFOS = [
  { key: 'alarm_code', label: '故障码' },
  { key: 'timer_schedule', label: '定时计划' },
  { key: 'alarm', label: '运行状态' },
];

const ACTIONS = [
  { key: 'filterReset', label: '滤网复位' },
];

const POWER_SVG = (color) => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true"><path d="M12 2.5V11.5" stroke="${color}" stroke-width="2" stroke-linecap="round"/><path d="M6.7 5.6a8 8 0 1 0 10.6 0" stroke="${color}" stroke-width="2" stroke-linecap="round"/></svg>`;

// HA 图标集里的纳诺怡图标：由集成 frontend/panasonic_icons.js 通过
// window.customIcons.panasonic 注册，v2.6.2 起随集成自动注入前端，无需手动添加资源。
const NANOE_ICON = 'panasonic:nanoe';

// 同源降级标记：仅当 HA 未加载 panasonic 图标集时使用，
// 形状与 brand/nanoe.svg 一致（右侧切平的大圆盘 + 卫星圆点），避免出现空白图标。
// 用等效 path 表达直边，避免 shadow DOM 内 clipPath 的 url(#id) 片段引用失效。
const NANOE_LOGO_SVG = () => `<svg viewBox="0 0 44 44" fill="none" aria-hidden="true">
  <g transform="translate(4.2 6)" fill="currentColor">
    <path d="M22.6 10.63 A11 11 0 1 0 22.6 21.37 Z"/>
    <circle cx="29" cy="16" r="4.6"/>
  </g>
</svg>`;

class PanasonicClimateCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = null;
    this._climates = [];
    this._hass = null;
    this._drawer = false;
    this._panel = null;       // 'fan' | 'swing' | null
    this._swingPending = { v: null, h: null }; // 摆风本地待确认值 { value, from }
    this._swingTimer = null;  // 服务未回传时的兜底清除定时器
    this._lastMode = 'cool';
    this._history = { temp: [] };
    this._fanModes = [];      // 当前实体申报的风速档位，滑块按索引取值
    this._loading = false;
    this._lastLoad = 0;
    this._timer = null;
    this.shadowRoot.addEventListener('click', (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener('input', (ev) => this._onFanInput(ev));
    this.shadowRoot.addEventListener('change', (ev) => this._onFanChange(ev));
  }

  connectedCallback() {
    if (!this._timer) {
      this._timer = setInterval(() => this._loadHistory(true), 5 * 60 * 1000);
    }
  }

  disconnectedCallback() {
    if (this._timer) clearInterval(this._timer);
    this._timer = null;
    this._clearSwingPendingTimer();
  }

  setConfig(config) {
    // entity is optional: the card discovers every climate entity published
    // by this integration and picks one automatically.
    this._config = Object.assign({ show_charts: true }, config || {});
    if (this._hass) this._syncEntity();
    this._render();
    if (this._hass) this._loadHistory(true);
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    this._syncEntity();
    this._syncSwingPending();
    this._render();
    // 历史数据只在首次连接与 5 分钟轮询时取，避免每次状态变化都打接口
    if (first) this._loadHistory(true);
  }

  getCardSize() { return 10; }

  static getStubConfig() { return {}; }

  _state(id) {
    return id && this._hass && this._hass.states ? this._hass.states[id] : undefined;
  }

  // 集成在 climate 实体上发布的「key → entity_id」映射，按设备隔离。
  _entityMap() {
    const st = this._state(this._config && this._config.entity);
    const map = st && st.attributes && st.attributes.panasonic_entities;
    return map && typeof map === 'object' ? map : {};
  }

  // 把功能清单解析成带 id 的列表；用户显式提供的 id 优先。
  // 解析不到实体（未安装集成 / 功能未启用）的项直接隐藏。
  _list(name, defaults) {
    const override = this._config && this._config[name];
    const source = Array.isArray(override) ? override : defaults;
    const map = this._entityMap();
    return source
      .map((item) => Object.assign({}, item, { id: item.id || map[item.key] || null }))
      .filter((item) => item.id);
  }

  // 自动发现：带 panasonic_entities 属性的 climate 实体即本集成的设备。
  // 不依赖 entity_id 前缀、设备名或 hass.entities 的具体字段。
  _discover() {
    const states = (this._hass && this._hass.states) || {};
    return Object.keys(states)
      .filter((id) => id.indexOf('climate.') === 0
        && states[id].attributes
        && states[id].attributes.panasonic_entities)
      .sort();
  }

  _syncEntity() {
    const list = this._discover();
    this._climates = list;
    if (!list.length) return;
    const preferred = this._config && this._config.entity;
    if (!preferred || list.indexOf(preferred) < 0) {
      this._config = Object.assign({}, this._config || {}, { entity: list[0] });
    }
  }

  _cardName(st) {
    if (this._config && this._config.name) return this._config.name;
    const a = st && st.attributes ? st.attributes : {};
    return a.friendly_name || '空调';
  }

  _deviceSwitchHtml() {
    if (!this._climates || this._climates.length < 2) return '';
    const current = this._config && this._config.entity;
    return `<select class="device-switch" data-act="device-switch" aria-label="选择空调">
      ${this._climates.map((id) => {
        const st = this._state(id);
        const label = (st && st.attributes && st.attributes.friendly_name) || id;
        return `<option value="${this._esc(id)}" ${id === current ? 'selected' : ''}>${this._esc(label)}</option>`;
      }).join('')}
    </select>`;
  }

  _esc(value) {
    return String(value ?? '').replace(/[&<>"]/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
    }[c]));
  }

  // 显示中文标签；下发服务时仍用原始值
  _label(kind, value) {
    const map = LABELS[kind] || {};
    return Object.prototype.hasOwnProperty.call(map, value) ? map[value] : value;
  }

  _call(domain, service, data) {
    if (!this._hass || typeof this._hass.callService !== 'function') return;
    try {
      this._hass.callService(domain, service, data);
    } catch (err) {
      console.error('panasonic-climate-card:', service, err);
    }
  }

  // 摆风选中态：服务下发到实体状态回传之间，用本地值维持面板里的即时反馈。
  // 状态追上目标值、或被外部改成别的值时立即以实体为准；超时兜底避免服务失败留下假选中。
  _swingShown(axis, actual) {
    const pending = this._swingPending[axis];
    return pending ? pending.value : actual;
  }

  _syncSwingPending() {
    const p = this._swingPending;
    if (!p.v && !p.h) return;
    const st = this._config && this._state(this._config.entity);
    const a = st ? (st.attributes || {}) : {};
    [['v', 'swing_mode'], ['h', 'swing_horizontal_mode']].forEach(([axis, attr]) => {
      const item = p[axis];
      if (!item) return;
      const now = a[attr];
      if (now === item.value || (now !== undefined && now !== item.from)) p[axis] = null;
    });
    if (!p.v && !p.h) this._clearSwingPendingTimer();
  }

  _clearSwingPendingTimer() {
    if (this._swingTimer) clearTimeout(this._swingTimer);
    this._swingTimer = null;
  }

  _armSwingPendingTimer() {
    this._clearSwingPendingTimer();
    this._swingTimer = setTimeout(() => {
      this._swingTimer = null;
      this._swingPending = { v: null, h: null };
      this._render();
    }, 8000);
  }

  // 温度步进：显式配置 > 实体申报的 target_temp_step > 兜底 1℃
  _step(attrs) {
    const fromConfig = Number(this._config.step);
    if (Number.isFinite(fromConfig) && fromConfig > 0) return fromConfig;
    const fromEntity = Number(attrs.target_temp_step);
    if (Number.isFinite(fromEntity) && fromEntity > 0) return fromEntity;
    return 1;
  }

  // 由步进推导显示精度：1 → 整数，0.5 → 1 位小数
  _precision(step) {
    const text = String(step);
    return text.includes('.') ? text.split('.')[1].length : 0;
  }

  _temp(value, decimals = 0) {
    const num = Number(value);
    if (value === undefined || value === null || value === 'unknown' || !Number.isFinite(num)) return '--°';
    return `${num.toFixed(decimals)}°`;
  }

  // 室温按传感器实际值显示，整数不带多余的小数位
  _tempAuto(value) {
    const num = Number(value);
    if (value === undefined || value === null || value === 'unknown' || !Number.isFinite(num)) return '--°';
    return `${Number.isInteger(num) ? num : num.toFixed(1)}°`;
  }

  // ── 24h 温度曲线数据 ─────────────────────────────────────────────
  async _loadHistory(force) {
    if (!this._config || !this._hass || this._loading) return;
    const now = Date.now();
    if (!force && now - this._lastLoad < 5 * 60 * 1000) return;
    this._loading = true;
    this._lastLoad = now;
    try {
      const cfg = this._config;
      const startMs = now - 24 * 3600 * 1000;
      const start = new Date(startMs).toISOString();
      const end = new Date(now).toISOString();
      const tempEntity = cfg.temp_entity || cfg.entity;

      let rows = null;
      if (typeof this._hass.callWS === 'function') {
        rows = await this._hass.callWS({
          type: 'history/history_during_period',
          start_time: start,
          end_time: end,
          entity_ids: [tempEntity],
          include_start_time_state: true,
          significant_changes_only: false,
          minimal_response: false,
          no_attributes: false,
        });
      } else if (typeof this._hass.callApi === 'function') {
        rows = await this._hass.callApi('GET', `history/period/${start}`, {
          filter_entity_id: tempEntity,
          end_time: end,
          minimal_response: 'false',
          no_attributes: 'false',
        });
      }
      this._applyHistory(rows, tempEntity, startMs, now);
    } catch (err) {
      // 取不到历史就保持空状态，绝不生成虚构曲线
      console.warn('panasonic-climate-card: 24h 温度历史读取失败', err);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  // 把 HA 历史响应统一成 { entity_id: [state, ...] }
  _historyLists(rows) {
    const lists = {};
    if (Array.isArray(rows)) {
      rows.forEach((entry) => {
        if (Array.isArray(entry) && entry.length && entry[0]) {
          const id = entry[0].entity_id;
          if (id) lists[id] = entry;
        } else if (entry && typeof entry === 'object' && entry.entity_id) {
          (lists[entry.entity_id] = lists[entry.entity_id] || []).push(entry);
        }
      });
    } else if (rows && typeof rows === 'object') {
      Object.keys(rows).forEach((id) => {
        if (Array.isArray(rows[id])) lists[id] = rows[id];
      });
    }
    return lists;
  }

  // 把时间点压成 24 个整点桶，缺失前向填充
  _buckets(points, startMs, valueOf) {
    const N = 24;
    const HOUR = 3600000;
    const raw = new Array(N).fill(null);
    let count = 0;
    (points || []).forEach((p) => {
      const v = valueOf(p);
      if (!Number.isFinite(v)) return;
      const t = Date.parse(p.last_changed || p.last_updated || p.lc || p.lu || '');
      if (!Number.isFinite(t)) return;
      if (t < startMs) return;
      // 当前实时状态落在第 24 桶边界上，归入最后一桶
      const idx = Math.min(N - 1, Math.floor((t - startMs) / HOUR));
      raw[idx] = v;
      count += 1;
    });
    // 只有当前一帧读数不足以构成曲线，宁可显示空状态也不画平线
    if (count < 2) return [];
    const first = raw.find((v) => v !== null);
    for (let i = 0; i < N; i += 1) {
      if (raw[i] === null) raw[i] = i ? raw[i - 1] : first;
    }
    return raw.map((v) => Number(Number(v).toFixed(2)));
  }

  _applyHistory(rows, tempEntity, startMs, nowMs) {
    const lists = this._historyLists(rows);
    const nowIso = new Date(nowMs).toISOString();

    const climateState = this._state(tempEntity);
    const climateAttrs = climateState ? (climateState.attributes || {}) : {};
    const tempPoints = (lists[tempEntity] || []).slice();
    if (Number.isFinite(Number(climateAttrs.current_temperature))) {
      tempPoints.push({
        entity_id: tempEntity,
        attributes: { current_temperature: climateAttrs.current_temperature },
        last_changed: nowIso,
      });
    }
    const temp = this._buckets(
      tempPoints, startMs,
      (p) => Number(p.attributes && p.attributes.current_temperature)
    );
    this._history = { temp };
  }

  _chartSvg(kind, series, color, cardColor) {
    const W = 320;
    const H = 88;
    const TOP = 8;
    const BOTTOM = 76;
    const min = Math.min(...series);
    const max = Math.max(...series);
    const pad = Math.max(0.4, (max - min) * 0.18);
    const lo = min - pad;
    const hi = max + pad;
    const span = hi - lo || 1;
    const pts = series.map((v, i) => ({
      x: Number((i / (series.length - 1) * W).toFixed(2)),
      y: Number((BOTTOM - (v - lo) / span * (BOTTOM - TOP)).toFixed(2)),
    }));
    let line = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 1; i < pts.length; i += 1) {
      const prev = pts[i - 1];
      const cur = pts[i];
      const cx = Number(((prev.x + cur.x) / 2).toFixed(2));
      line += ` C ${cx} ${prev.y}, ${cx} ${cur.y}, ${cur.x} ${cur.y}`;
    }
    const area = `${line} L ${W} ${H} L 0 ${H} Z`;
    const last = pts[pts.length - 1];
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">
      <defs><linearGradient id="pc-grad-${kind}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${color}" stop-opacity=".20"/>
        <stop offset="1" stop-color="${color}" stop-opacity="0"/>
      </linearGradient></defs>
      <line x1="0" y1="24" x2="${W}" y2="24" stroke="${color}" stroke-opacity=".10" stroke-width="1" vector-effect="non-scaling-stroke"/>
      <line x1="0" y1="56" x2="${W}" y2="56" stroke="${color}" stroke-opacity=".10" stroke-width="1" vector-effect="non-scaling-stroke"/>
      <path d="${area}" fill="url(#pc-grad-${kind})"/>
      <path d="${line}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>
      <circle cx="${last.x}" cy="${last.y}" r="3.2" fill="${color}" stroke="${cardColor}" stroke-width="1.5" vector-effect="non-scaling-stroke"/>
    </svg>`;
  }

  _chartHtml(series, color, cardColor) {
    const has = Array.isArray(series) && series.length >= 2;
    const valueText = has ? `${series[series.length - 1]}°` : '—';
    const plot = has
      ? this._chartSvg('temp', series, color, cardColor)
      : `<svg viewBox="0 0 320 88" preserveAspectRatio="none" aria-hidden="true"><line x1="0" y1="46" x2="320" y2="46" stroke="${color}" stroke-opacity=".32" stroke-width="1.5" stroke-dasharray="4 6" vector-effect="non-scaling-stroke"/></svg>`;
    return `<div class="chart">
      <div class="chart-head">
        <span class="chart-title">24 小时温度</span>
        <span class="chart-value">${this._esc(valueText)}</span>
      </div>
      <div class="chart-plot">${plot}${has ? '' : '<div class="chart-empty"><span>暂无 24 小时数据</span></div>'}</div>
      <div class="chart-axis"><span>24 小时前</span><span>12 小时前</span><span>现在</span></div>
    </div>`;
  }

  // 传感器读数：实体缺失 / 无效值一律显示「—」，绝不编造数值
  _sensorText(id, isCost) {
    const st = this._state(id);
    if (!st) return null;
    const raw = String(st.state ?? '').trim();
    if (!raw || ['--', 'unknown', 'unavailable', 'none', 'null', 'n/a'].includes(raw.toLowerCase())) return '—';
    const unit = (st.attributes && st.attributes.unit_of_measurement) || '';
    if (unit) return `${raw} ${unit}`;
    return isCost ? `¥ ${raw}` : raw;
  }

  // 主卡常驻的两个费用读数
  _sensorsHtml() {
    const items = this._list('cost_main', COST_MAIN).filter((s) => this._state(s.id));
    return `<div class="sensors">${items.map((s) => {
      const value = this._sensorText(s.id, s.cost) ?? '—';
      return `<div class="sensor">
        <span class="sensor-label">${this._esc(s.label)}</span>
        <span class="sensor-value">${this._esc(value)}</span>
      </div>`;
    }).join('')}</div>`;
  }

  // 纳诺怡图标优先级：nanoe_logo 图片 > HA 图标集 panasonic:nanoe > 同源内置矢量（降级）。
  // 图标集的 path 跟随 currentColor，颜色由 .pin-icon 上的 --pc-nanoe-on / --pc-indicator-off 决定。
  _iconSetAvailable() {
    const sets = typeof window !== 'undefined' ? window.customIcons : null;
    const panasonic = sets && sets.panasonic;
    return !!(panasonic && typeof panasonic.getIcon === 'function');
  }

  _nanoeLogoHtml() {
    const src = this._config && this._config.nanoe_logo;
    if (typeof src === 'string' && src.trim()) {
      return `<img src="${this._esc(src.trim())}" alt="" aria-hidden="true">`;
    }
    if (this._iconSetAvailable()) {
      return `<ha-icon icon="${NANOE_ICON}" aria-hidden="true"></ha-icon>`;
    }
    return NANOE_LOGO_SVG();
  }

  _pinsHtml() {
    return this._list('pinned', PINNED).map((p) => {
      const st = this._state(p.id);
      const available = !!st;
      const on = available && st.state === 'on';
      const color = on
        ? (p.kind === 'light' ? 'var(--pc-light-on)' : 'var(--pc-nanoe-on)')
        : 'var(--pc-indicator-off)';
      const icon = p.kind === 'light'
        ? `<span class="dot" style="background:${color}"></span>`
        : `<span class="pin-icon" style="color:${color}">${this._nanoeLogoHtml()}</span>`;
      const attrs = available
        ? `data-act="toggle" data-entity="${this._esc(p.id)}" data-on="${on ? '1' : '0'}"`
        : 'disabled';
      // 视觉上只保留图标；名称放进 title / aria-label，悬停与读屏仍可辨认
      return `<button class="pin ${p.kind} ${on ? 'on' : 'off'}" ${attrs}
        title="${this._esc(p.label)} · ${on ? '开' : '关'}"
        aria-label="${this._esc(p.label)} · ${on ? '开' : '关'}">${icon}</button>`;
    }).join('');
  }

  _render() {
    if (!this._config || !this._hass) return;
    const cfg = this._config;
    const st = this._state(cfg.entity);
    const root = this.shadowRoot;

    const theme = THEME;

    if (!st) {
      const hint = this._climates && this._climates.length
        ? `找不到实体 ${this._esc(cfg.entity || '')}`
        : '未找到 CS-ZY35K410 集成的空调实体，请先在「设置 → 设备与服务」添加集成并刷新页面';
      root.innerHTML = `<style>${this._css(theme)}</style><ha-card class="card"><div class="missing">${hint}</div></ha-card>`;
      return;
    }

    const a = st.attributes || {};
    // 摆风显示值：服务已回传用实体真实值，未回传期间用本地待确认值
    const swingVShown = this._swingShown('v', a.swing_mode);
    const swingHShown = this._swingShown('h', a.swing_horizontal_mode);
    const mode = st.state === 'off' ? 'off' : st.state;
    if (st.state !== 'off') this._lastMode = st.state;
    const accent = theme.accents[mode] || theme.accents.off;
    const gradient = theme.gradients[mode] || theme.gradients.off;
    const hvacModes = Array.isArray(a.hvac_modes) ? a.hvac_modes : [];
    // 只显示 climate 实体真实申报的模式，不硬造「自动」
    const modes = MODES.filter((m) => hvacModes.length === 0 || hvacModes.includes(m.v));
    const fanModes = Array.isArray(a.fan_modes) ? a.fan_modes : [];
    const swingV = Array.isArray(a.swing_modes) ? a.swing_modes : [];
    const swingH = Array.isArray(a.swing_horizontal_modes) ? a.swing_horizontal_modes : [];
    this._fanModes = fanModes.slice();

    const availableSwitches = this._list('switches', SWITCHES).filter((s) => this._state(s.id));
    const availableInfos = this._list('infos', INFOS).filter((s) => this._state(s.id));
    const availableActions = this._list('actions', ACTIONS).filter((s) => this._state(s.id));
    const availableCosts = this._list('cost_extra', COST_EXTRA).filter((s) => this._state(s.id));

    const step = this._step(a);
    const precision = this._precision(step);
    const roomLine = a.current_temperature !== undefined && a.current_temperature !== null
      ? `室内 ${this._tempAuto(a.current_temperature)}` : '当前温度不可用';

    // 已开启的进阶功能写进副行；灯与纳诺怡已在状态位固定显示，不重复罗列
    const pinnedIds = this._list('pinned', PINNED).map((p) => p.id);
    const activeNames = availableSwitches
      .filter((s) => this._state(s.id).state === 'on' && !pinnedIds.includes(s.id))
      .map((s) => s.label);
    const activeText = activeNames.length
      ? activeNames.slice(0, 3).join(' · ') + (activeNames.length > 3 ? ` 等 ${activeNames.length} 项` : '')
      : '';
    const subLine = [roomLine, activeText].filter(Boolean).join(' · ');

    // 主卡：24h 温度曲线 + 费用传感器读数
    const analytics = `<div class="charts">
      ${cfg.show_charts === false ? '' : this._chartHtml(this._history.temp, theme.v.chartTemp, theme.v.card)}
      ${this._sensorsHtml()}
    </div>`;

    root.innerHTML = `
      <style>${this._css(theme, accent, gradient)}</style>
      <ha-card class="card">
        <div class="hero">
          <div class="hero-top">
            <div class="hero-name">
              <div class="title">${this._esc(this._cardName(st))}</div>
              <div class="sub">${this._esc(subLine)}</div>
            </div>
            ${this._deviceSwitchHtml()}
            <button class="power" data-act="power" aria-label="电源">${POWER_SVG(accent)}</button>
          </div>
          <div class="big">${this._temp(a.temperature, precision)}</div>
          <div class="pins">${this._pinsHtml()}</div>
        </div>

        <div class="body">
          <div class="segmented">
            ${modes.map((m) => `<button class="seg ${st.state === m.v ? 'active' : ''}" data-act="mode" data-value="${m.v}">${m.t}</button>`).join('')}
          </div>

          <div class="quick">
            <button class="tile ${this._panel === 'fan' ? 'selected' : ''}" data-act="fanpanel" ${fanModes.length ? '' : 'disabled'}>
              <span class="tile-label">风速</span><span class="tile-value">${this._esc(this._label('fan', a.fan_mode || 'auto'))}</span>
            </button>
            <button class="tile ${this._panel === 'swing' ? 'selected' : ''}" data-act="swingpanel" ${(swingV.length || swingH.length) ? '' : 'disabled'}>
              <span class="tile-label">摆风</span><span class="tile-value">${this._esc(this._label('swingV', swingVShown || 'Auto'))}</span>
            </button>
            <button class="tile more" data-act="more">
              <span class="tile-value">更多</span>
            </button>
          </div>

          ${this._panel === 'fan' && fanModes.length ? this._fanPanelHtml(fanModes, a.fan_mode) : ''}

          ${this._panel === 'swing' && (swingV.length || swingH.length) ? `
            <div class="inline">
              ${swingV.length ? `<div class="inline-title">上下摆风</div><div class="chips">${swingV.map((s) => `<button class="chip ${swingVShown === s ? 'on' : ''}" data-act="swing" data-axis="v" data-value="${this._esc(s)}">${this._esc(this._label('swingV', s))}</button>`).join('')}</div>` : ''}
              ${swingH.length ? `<div class="inline-title">左右摆风</div><div class="chips">${swingH.map((s) => `<button class="chip ${swingHShown === s ? 'on' : ''}" data-act="swing" data-axis="h" data-value="${this._esc(s)}">${this._esc(this._label('swingH', s))}</button>`).join('')}</div>` : ''}
            </div>` : ''}

          <div class="stepper">
            <button class="round" data-act="temp" data-dir="-1" aria-label="降温">−</button>
            <span class="track"></span>
            <button class="round" data-act="temp" data-dir="1" aria-label="升温">+</button>
          </div>

          ${analytics}
        </div>

        ${this._drawer ? this._drawerHtml(availableSwitches, availableInfos, availableActions, availableCosts) : ''}
      </ha-card>
    `;
  }

  // 风速面板：滑块档位来自实体申报的 fan_modes，索引与原始值一一对应
  _fanPanelHtml(fanModes, current) {
    const n = fanModes.length;
    let idx = fanModes.indexOf(current);
    if (idx < 0) idx = 0;
    const fill = n > 1 ? (idx / (n - 1) * 100).toFixed(1) : '0';
    return `<div class="inline fan-panel">
      <div class="fan-head">
        <span class="inline-title">风速</span>
        <span class="fan-value" data-role="fan-value">${this._esc(this._label('fan', fanModes[idx]))}</span>
      </div>
      <input class="fan-range" type="range" min="0" max="${n - 1}" step="1" value="${idx}"
             data-act="fanrange" aria-label="风速档位" style="--pc-fan-fill:${fill}%">
      <div class="fan-ticks" data-role="fan-ticks">${fanModes.map((f, i) => `<i class="${i === idx ? 'on' : ''}"></i>`).join('')}</div>
      <div class="fan-scale">
        <span>${this._esc(this._label('fan', fanModes[0]))}</span>
        <span>${this._esc(this._label('fan', fanModes[n - 1]))}</span>
      </div>
    </div>`;
  }

  _drawerHtml(switches, infos, actions, costs) {
    return `
      <div class="overlay" data-act="close"></div>
      <div class="sheet" role="dialog" aria-label="更多功能">
        <div class="grab"></div>
        <div class="sheet-head">
          <div class="sheet-title">更多功能</div>
          <button class="close" data-act="close" aria-label="关闭">关闭</button>
        </div>
        <div class="grid">
          ${switches.map((s) => {
            const on = this._state(s.id).state === 'on';
            return `<button class="sw ${on ? 'on' : ''}" data-act="toggle" data-entity="${this._esc(s.id)}" data-on="${on ? '1' : '0'}">
              <span>${this._esc(s.label)}</span><span class="sw-state">${on ? '开' : '关'}</span>
            </button>`;
          }).join('')}
        </div>
        ${(costs || []).length ? `<div class="costs">
          <div class="costs-title">费用与用电</div>
          ${costs.map((s) => `<div class="info-row"><span>${this._esc(s.label)}</span><span>${this._esc(this._sensorText(s.id, s.cost) ?? '—')}</span></div>`).join('')}
        </div>` : ''}
        ${infos.length ? `<div class="infos">${infos.map((s) => `<div class="info-row"><span>${this._esc(s.label)}</span><span>${this._esc(this._state(s.id).state)}</span></div>`).join('')}</div>` : ''}
        ${actions.length ? `<div class="actions">${actions.map((s) => `<button class="action" data-act="button" data-entity="${this._esc(s.id)}">${this._esc(s.label)}</button>`).join('')}</div>` : ''}
      </div>
    `;
  }

  // 拖动滑块：只更新档位文字 / 填充 / 刻度，不重渲染也不发服务
  _onFanInput(ev) {
    const el = ev.target;
    if (!el || !el.dataset || el.dataset.act !== 'fanrange') return;
    const idx = Number(el.value);
    const modes = this._fanModes;
    if (!modes.length || !Object.prototype.hasOwnProperty.call(modes, idx)) return;
    const n = modes.length;
    el.style.setProperty('--pc-fan-fill', `${n > 1 ? (idx / (n - 1) * 100).toFixed(1) : 0}%`);
    const label = this.shadowRoot.querySelector('[data-role="fan-value"]');
    if (label) label.textContent = this._label('fan', modes[idx]);
    this.shadowRoot.querySelectorAll('[data-role="fan-ticks"] i')
      .forEach((tick, i) => tick.classList.toggle('on', i === idx));
  }

  // 松手才下发服务，档位值用实体申报的原始字符串
  _onFanChange(ev) {
    const el = ev.target;
    if (!el || !el.dataset) return;
    if (el.dataset.act === 'device-switch') {
      const id = el.value;
      if (this._climates && this._climates.indexOf(id) >= 0) {
        this._config = Object.assign({}, this._config, { entity: id });
        this._drawer = false;
        this._panel = null;
        this._render();
        this._loadHistory(true);
      }
      return;
    }
    if (el.dataset.act !== 'fanrange') return;
    const mode = this._fanModes[Number(el.value)];
    if (!mode || !this._config) return;
    this._call('climate', 'set_fan_mode', { entity_id: this._config.entity, fan_mode: mode });
  }

  _onClick(ev) {
    const el = ev.target.closest('[data-act]');
    if (!el || !this._config || !this._hass) return;
    const act = el.dataset.act;
    const cfg = this._config;
    const st = this._state(cfg.entity);
    const a = st ? (st.attributes || {}) : {};

    switch (act) {
      case 'power':
        if (st.state === 'off') {
          this._call('climate', 'set_hvac_mode', { entity_id: cfg.entity, hvac_mode: this._lastMode });
        } else {
          this._call('climate', 'set_hvac_mode', { entity_id: cfg.entity, hvac_mode: 'off' });
        }
        break;
      case 'temp': {
        const step = this._step(a);
        const min = Number(a.min_temp ?? 16);
        const max = Number(a.max_temp ?? 30);
        const base = Number(a.temperature);
        if (!Number.isFinite(base)) break;
        // 按实体步进对齐，避免半度/整度混用与浮点尾数
        const raw = base + Number(el.dataset.dir) * step;
        const aligned = Number((Math.round(raw / step) * step).toFixed(2));
        const next = Math.min(max, Math.max(min, aligned));
        this._call('climate', 'set_temperature', { entity_id: cfg.entity, temperature: next });
        break;
      }
      case 'mode':
        this._call('climate', 'set_hvac_mode', { entity_id: cfg.entity, hvac_mode: el.dataset.value });
        break;
      case 'swing': {
        const axis = el.dataset.axis === 'h' ? 'h' : 'v';
        const value = el.dataset.value;
        const attr = axis === 'h' ? 'swing_horizontal_mode' : 'swing_mode';
        const service = axis === 'h' ? 'set_swing_horizontal_mode' : 'set_swing_mode';
        this._swingPending[axis] = { value, from: a[attr] };
        this._armSwingPendingTimer();
        this._call('climate', service, { entity_id: cfg.entity, [attr]: value });
        // 选完保持展开：只有再次点击「摆风」方块、切到别的面板或刷新页面才收起
        this._render();
        break;
      }
      case 'fanpanel':
        this._panel = this._panel === 'fan' ? null : 'fan';
        this._render();
        break;
      case 'swingpanel':
        this._panel = this._panel === 'swing' ? null : 'swing';
        this._render();
        break;
      case 'more':
        this._drawer = true;
        this._render();
        break;
      case 'close':
        this._drawer = false;
        this._render();
        break;
      case 'toggle':
        this._call('switch', el.dataset.on === '1' ? 'turn_off' : 'turn_on', { entity_id: el.dataset.entity });
        break;
      case 'button':
        this._call('button', 'press', { entity_id: el.dataset.entity });
        break;
      default:
        break;
    }
  }

  _css(theme = THEME, accent = theme.accents.cool, gradient = theme.gradients.cool) {
    const vars = Object.entries(theme.v)
      .map(([k, val]) => `--pc-${k.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}: ${val};`)
      .join('\n        ');
    return `
      :host {
        ${vars}
        --pc-accent: ${accent};
        --pc-hero: ${gradient};
        --pc-on-text: ${theme.onText || '#FFFFFF'};
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", "Noto Sans SC", "Helvetica Neue", sans-serif;
      }
      * { box-sizing: border-box; }
      .card { display: block; background: var(--pc-card); border: var(--pc-border); border-radius: var(--pc-radius);
              overflow: hidden; box-shadow: var(--pc-shadow); color: var(--pc-text); position: relative; }
      button { font: inherit; border: 0; cursor: pointer; background: none; color: inherit; }
      button:disabled { opacity: .45; cursor: default; }

      .hero { background: var(--pc-hero); padding: 26px; min-height: 250px; display: flex; flex-direction: column; gap: 10px; }
      .hero-top { display: flex; align-items: center; justify-content: space-between; height: 44px; gap: 12px; }
      .device-switch { max-width: 132px; font-size: 12px; color: var(--pc-text);
        background: var(--pc-pin-bg); border: 0; border-radius: 10px;
        padding: 6px 8px; outline: none; cursor: pointer; }
      .hero-name { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
      .title { font-size: 17px; font-weight: 600; }
      .sub { font-size: 12px; color: var(--pc-sub); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
      .power { flex: none; width: 44px; height: 44px; border-radius: 50%; background: var(--pc-power); display: grid; place-items: center;
               box-shadow: var(--pc-power-shadow); }
      .big { font-size: 76px; font-weight: 200; letter-spacing: -3px; line-height: 1.15; margin-top: 12px; }
      .missing { padding: 24px; font-size: 14px; color: var(--pc-inactive); }

      .pins { display: flex; gap: 8px; margin-top: auto; }
      .pin { width: 34px; height: 34px; padding: 0; border-radius: 50%; background: var(--pc-pin-bg);
             display: inline-grid; place-items: center; }
      .pin .dot { width: 10px; height: 10px; border-radius: 50%; flex: none; }
      .pin .pin-icon { display: inline-flex; align-items: center; flex: none; }
      .pin .pin-icon svg { width: 18px; height: 18px; }
      .pin.nanoe .pin-icon svg { width: 30px; height: 30px; }
      .pin.nanoe .pin-icon img { width: 30px; height: 30px; object-fit: contain; }
      .pin.nanoe ha-icon { --mdc-icon-size: 30px; width: 30px; height: 30px;
                           display: inline-flex; color: inherit; }
      .pin.nanoe.on .pin-icon { filter: drop-shadow(0 0 5px var(--pc-nanoe-glow)); }
      .pin.off .dot { box-shadow: inset 0 0 0 1px rgba(0,0,0,.06); }
      .pin.off .pin-icon img { filter: grayscale(1); opacity: .7; }

      .body { padding: 26px; display: flex; flex-direction: column; gap: 16px; }
      .segmented { display: flex; gap: 4px; padding: 4px; border-radius: 999px; background: var(--pc-surface); height: 44px; }
      .seg { flex: 1; border: 1px solid transparent; border-radius: 999px; font-size: 13px; color: var(--pc-inactive); }
      .seg.active { background: var(--pc-raised); border: var(--pc-active-border); color: var(--pc-accent);
                    font-weight: 600; box-shadow: var(--pc-seg-shadow); }

      .quick { display: flex; gap: 10px; }
      .tile { flex: 1; height: 72px; border: var(--pc-tile-border); border-radius: var(--pc-tile-radius);
              background: var(--pc-tile); padding: 14px; display: flex; flex-direction: column;
              align-items: center; justify-content: center; gap: 4px; }
      .tile.selected { outline: 2px solid var(--pc-accent); }
      .tile.more { background: var(--pc-more); border: var(--pc-more-border); color: var(--pc-accent); }
      .tile-label { font-size: 12px; color: var(--pc-label); }
      .tile.more .tile-value { color: var(--pc-accent); }
      .tile-value { font-size: 15px; font-weight: 600; }

      .inline { border-top: 1px solid var(--pc-line); padding-top: 14px; display: flex; flex-direction: column; gap: 8px; }
      .inline-title { font-size: 12px; color: var(--pc-muted); }
      .chips { display: flex; flex-wrap: wrap; gap: 8px; }
      .chip { padding: 8px 14px; border-radius: 999px; background: var(--pc-surface); font-size: 13px; color: var(--pc-inactive); }
      .chip.on { background: var(--pc-accent); color: var(--pc-on-text); }

      .fan-panel { gap: 9px; }
      .fan-head { display: flex; align-items: baseline; justify-content: space-between; }
      .fan-value { font-size: 17px; font-weight: 600; color: var(--pc-accent); }
      .fan-range { -webkit-appearance: none; appearance: none; width: 100%; height: 6px; margin: 7px 0 2px;
                   border-radius: 999px; outline: none; cursor: pointer;
                   background: linear-gradient(90deg,
                     var(--pc-accent) 0%, var(--pc-accent) var(--pc-fan-fill, 0%),
                     var(--pc-placeholder) var(--pc-fan-fill, 0%), var(--pc-placeholder) 100%); }
      .fan-range::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 24px; height: 24px;
                   border-radius: 50%; background: var(--pc-raised); border: 1px solid var(--pc-line);
                   box-shadow: var(--pc-seg-shadow); cursor: grab; }
      .fan-range::-moz-range-thumb { width: 24px; height: 24px; border-radius: 50%;
                   background: var(--pc-raised); border: 1px solid var(--pc-line);
                   box-shadow: var(--pc-seg-shadow); cursor: grab; }
      .fan-range:active::-webkit-slider-thumb { cursor: grabbing; }
      .fan-ticks { display: flex; justify-content: space-between; padding: 0 11px; }
      .fan-ticks i { width: 4px; height: 4px; border-radius: 50%; background: var(--pc-placeholder); }
      .fan-ticks i.on { background: var(--pc-accent); }
      .fan-scale { display: flex; justify-content: space-between; font-size: 11px; color: var(--pc-faint); }

      .stepper { display: flex; align-items: center; justify-content: space-between; gap: 8px;
                 background: var(--pc-surface); border-radius: 16px; padding: 8px; height: 56px; }
      .round { width: 56px; height: 40px; border-radius: 12px; background: var(--pc-raised); font-size: 20px; line-height: 1; }
      .track { flex: 1; height: 1px; background: var(--pc-line); margin: 0 10px; }

      .charts { display: flex; flex-direction: column; gap: 10px; }
      .chart { background: var(--pc-surface); border-radius: 16px; padding: 14px 16px 10px; }
      .chart-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
      .chart-title { font-size: 12px; color: var(--pc-muted); }
      .chart-value { font-size: 15px; font-weight: 600; color: var(--pc-value); font-variant-numeric: tabular-nums; }
      .chart-plot { position: relative; }
      .chart-plot svg { display: block; width: 100%; height: 76px; margin-top: 6px; }
      .chart-empty { position: absolute; inset: 0; display: grid; place-items: center;
                     font-size: 12px; color: var(--pc-faint); }
      .chart-empty span { background: var(--pc-surface); padding: 0 8px; }
      .chart-axis { display: flex; justify-content: space-between; font-size: 10px; color: var(--pc-faint); margin-top: 2px; }

      .sensors { display: flex; gap: 10px; }
      .sensor { flex: 1; min-width: 0; background: var(--pc-surface); border-radius: 16px; padding: 14px 16px;
                display: flex; flex-direction: column; gap: 6px; }
      .sensor-label { font-size: 12px; color: var(--pc-muted); }
      .sensor-value { font-size: 21px; font-weight: 600; color: var(--pc-value); letter-spacing: -.4px;
                      font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

      .overlay { position: absolute; inset: 0; background: var(--pc-overlay); z-index: 2; }
      .sheet { position: absolute; left: 0; right: 0; bottom: 0; z-index: 3; background: var(--pc-sheet);
               border-radius: var(--pc-radius) var(--pc-radius) 0 0; padding: 20px 24px 24px;
               display: flex; flex-direction: column; gap: 12px; box-shadow: var(--pc-sheet-shadow);
               max-height: calc(100% - 12px); overflow-y: auto; }
      .grab { width: 36px; height: 4px; border-radius: 2px; background: var(--pc-placeholder); align-self: center; }
      .sheet-head { display: flex; align-items: center; justify-content: space-between; }
      .sheet-title { font-size: 20px; font-weight: 600; }
      .close { font-size: 13px; color: var(--pc-accent); }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
      .sw { height: 44px; border-radius: 12px; background: var(--pc-surface); padding: 0 12px;
            display: flex; align-items: center; justify-content: space-between; font-size: 13px; color: var(--pc-inactive); }
      .sw.on { background: var(--pc-more); color: var(--pc-accent); font-weight: 500; }
      .sw-state { opacity: .7; }
      .costs { border-top: 1px solid var(--pc-line); padding-top: 10px; display: flex; flex-direction: column; gap: 8px; }
      .costs-title { font-size: 12px; font-weight: 600; color: var(--pc-text); }
      .infos { border-top: 1px solid var(--pc-line); padding-top: 10px; display: flex; flex-direction: column; gap: 8px; }
      .info-row { display: flex; justify-content: space-between; font-size: 13px; color: var(--pc-muted); gap: 12px; }
      .info-row span:last-child { color: var(--pc-value); font-variant-numeric: tabular-nums; }
      .actions { display: flex; gap: 8px; }
      .action { padding: 10px 16px; border-radius: 12px; background: var(--pc-surface); font-size: 13px; }
    `;
  }
}

if (!customElements.get('panasonic-climate-card')) {
  customElements.define('panasonic-climate-card', PanasonicClimateCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === 'panasonic-climate-card')) {
  window.customCards.push({
    type: 'panasonic-climate-card',
    name: '松下 CS-ZY35K410 空调',
    description: '集成自带，开箱即用：自动发现实体，支持多台同型号空调；霜白主题、24h 温度曲线与费用读数',
    preview: true,
  });
}
