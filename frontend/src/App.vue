<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { createChart, CandlestickSeries, HistogramSeries, ColorType } from 'lightweight-charts'

const symbol = ref('AAPL'), interval = ref('1m'), mode = ref('live'), dataset = ref('live')
const data = ref(null), connected = ref(false), error = ref(''), sessions = ref([])
const chartEl = ref(null), hover = ref(null), now = ref(Date.now() / 1000)
const start = ref(''), end = ref(''), speed = ref(10), busy = ref(false)
let chart, candles, volume, socket, timer, retry, generation = 0, previous = []
const names = { AAPL: 'Apple Inc.', MSFT: 'Microsoft Corporation', 'BTC-USD': 'Bitcoin / US Dollar' }
const bars = computed(() => data.value?.candles || [])
const last = computed(() => bars.value.at(-1))
const selected = computed(() => hover.value || last.value)
const stats = computed(() => data.value?.stats || { deliveries: 0, observations: 0, duplicates: 0, effective: 0 })
const feed = computed(() => data.value?.feed || { state: 'connecting', detail: 'Connecting to backend…' })
const latest = computed(() => data.value?.latest)
const age = computed(() => latest.value ? Math.max(0, (mode.value === 'replay' ? data.value.clock : now.value) - latest.value.source_time) : null)
const ageText = computed(() => age.value === null ? 'No observations' : age.value < 60 ? `${Math.floor(age.value)}s` : age.value < 3600 ? `${Math.floor(age.value / 60)}m ${Math.floor(age.value % 60)}s` : `${Math.floor(age.value / 3600)}h ${Math.floor(age.value % 3600 / 60)}m`)
const statusLabel = computed(() => {
  if (!connected.value) return 'Backend offline'
  if (mode.value === 'replay') return data.value?.playing ? 'Replaying' : 'Replay paused'
  if (feed.value.state !== 'connected') return { disconnected: 'Feed disconnected', connecting: 'Connecting to Yahoo', unavailable: 'Feed unavailable' }[feed.value.state] || feed.value.state
  return age.value === null ? 'Waiting for observations' : age.value > 60 ? 'Source data stale' : 'Receiving Yahoo data'
})
const change = computed(() => bars.value.length ? last.value.close - bars.value[0].open : null)
const rangeSessions = computed(() => sessions.value.filter(s => s.dataset === dataset.value && s.symbol === symbol.value))
const format = (n, digits = 2) => n == null ? '—' : Number(n).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
const stamp = (t) => t == null ? '—' : new Date(t * 1000).toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
const shortTime = (t) => t == null ? '—' : new Date(t * 1000).toISOString().slice(11, 19)

async function refreshSessions() {
  try {
    const response = await fetch('/api/sessions')
    if (!response.ok) throw new Error('Could not read saved sessions')
    sessions.value = (await response.json()).sessions
  } catch (e) { error.value = e.message }
}
function command(action, extra = {}) {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ action, ...extra }))
}
function openStream() {
  const id = ++generation
  clearTimeout(retry)
  if (socket) { socket.onclose = null; socket.close() }
  connected.value = false; data.value = null; hover.value = null; previous = []
  if (candles) { candles.setData([]); volume.setData([]) }
  const query = new URLSearchParams({ symbol: symbol.value, interval: interval.value, mode: mode.value, dataset: dataset.value })
  if (mode.value === 'replay') {
    if (start.value) query.set('start', new Date(start.value + 'Z').getTime() / 1000)
    if (end.value) query.set('end', new Date(end.value + 'Z').getTime() / 1000)
  }
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/market?${query}`)
  socket.onopen = () => { if (id === generation) { connected.value = true; error.value = ''; command('speed', { batch: speed.value }) } }
  socket.onmessage = (e) => {
    if (id !== generation) return
    const payload = JSON.parse(e.data)
    data.value = payload
    draw(payload.candles)
  }
  socket.onclose = (e) => {
    if (id !== generation) return
    connected.value = false
    if (e.code === 1008) { error.value = e.reason; return }
    error.value = 'Backend connection lost. Reconnecting…'
    retry = setTimeout(openStream, 3000)
  }
}
function draw(rows) {
  if (!candles) return
  const priceRows = rows.map(c => ({ time: c.timestamp, open: c.open, high: c.high, low: c.low, close: c.close }))
  const volumeRows = rows.map(c => c.volume == null ? { time: c.timestamp } : { time: c.timestamp, value: c.volume, color: c.close >= c.open ? '#267c6f' : '#974b5a' })
  const wasEmpty = previous.length === 0
  const needsRebuild = rows.length < previous.length || previous.some((old, i) =>
    rows[i]?.timestamp !== old.timestamp || (i < previous.length - 1 && JSON.stringify(rows[i]) !== JSON.stringify(old)))
  if (needsRebuild || wasEmpty) {
    candles.setData(priceRows); volume.setData(volumeRows)
  } else {
    rows.forEach((c, i) => {
      if (JSON.stringify(c) !== JSON.stringify(previous[i])) {
        candles.update(priceRows[i]); volume.update(volumeRows[i])
      }
    })
  }
  if ((wasEmpty || (mode.value === 'replay' && data.value?.playing)) && rows.length) chart.timeScale().fitContent()
  previous = rows.map(r => ({ ...r }))
}
function setMode(value, source = 'live') {
  mode.value = value; dataset.value = source; start.value = ''; end.value = ''
  if (source === 'demo') symbol.value = 'AAPL'
  refreshSessions()
}
async function toggleFeed() {
  busy.value = true
  try {
    const response = await fetch(`/api/feed/${['connected', 'connecting'].includes(feed.value.state) ? 'disconnect' : 'connect'}`, { method: 'POST' })
    if (!response.ok) throw new Error('Feed control failed')
    const state = await response.json()
    if (data.value) data.value.feed = state
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
watch([symbol, interval, mode, dataset], () => { openStream(); refreshSessions() })
onMounted(async () => {
  await nextTick()
  chart = createChart(chartEl.value, {
    autoSize: true, layout: { background: { type: ColorType.Solid, color: '#111923' }, textColor: '#8191a6', fontFamily: 'Consolas, monospace', fontSize: 11, attributionLogo: true },
    grid: { vertLines: { color: '#1b2632' }, horzLines: { color: '#1b2632' } },
    rightPriceScale: { borderColor: '#263240' },
    timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#263240', rightOffset: 5 },
    crosshair: { mode: 0, vertLine: { color: '#67768a', labelBackgroundColor: '#344358' }, horzLine: { color: '#67768a', labelBackgroundColor: '#344358' } },
    localization: { timeFormatter: (t) => stamp(t) }
  })
  candles = chart.addSeries(CandlestickSeries, { upColor: '#3ac5a0', downColor: '#ed7181', borderVisible: false, wickUpColor: '#3ac5a0', wickDownColor: '#ed7181', priceFormat: { type: 'price', precision: 2, minMove: .01 } })
  volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: '' }, 1)
  chart.panes()[0].setStretchFactor(4)
  chart.panes()[1].setStretchFactor(1)
  chart.subscribeCrosshairMove(p => { hover.value = p.time ? bars.value.find(c => c.timestamp === p.time) || null : null })
  timer = setInterval(() => { now.value = Date.now() / 1000 }, 1000)
  openStream(); refreshSessions()
})
onBeforeUnmount(() => { generation++; clearInterval(timer); clearTimeout(retry); socket?.close(); chart?.remove() })
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Market Desk home"><span class="brand-icon">▥</span>MARKET<span class="brand-light">DESK</span><span class="local-tag">LOCAL</span></a>
      <div class="top-links"><span class="top-active">Workstation</span><span class="muted">Part 4.1 · Market data</span></div>
      <div class="clock"><span class="tiny-dot" :class="{ good: connected }"></span>{{ shortTime(now) }} <span class="muted">UTC</span></div>
    </header>

    <aside class="sidebar">
      <div class="side-label">WORKSPACE</div>
      <div class="nav-selected"><span>▦</span> Market overview <span class="nav-arrow">↗</span></div>
      <div class="watchlist-heading"><span class="side-label">INSTRUMENTS</span><span class="muted">03</span></div>
      <button v-for="s in ['AAPL', 'MSFT', 'BTC-USD']" :key="s" class="watch-item" :class="{ active: symbol === s }" @click="symbol = s" :disabled="dataset === 'demo' && s !== 'AAPL'">
        <span class="ticker-icon" :class="s === 'BTC-USD' ? 'orange' : ''">{{ s === 'BTC-USD' ? '₿' : s === 'AAPL' ? 'A' : 'M' }}</span>
        <span><strong>{{ s }}</strong><small>{{ s === 'AAPL' ? 'Apple Inc.' : s === 'MSFT' ? 'Microsoft' : 'Bitcoin' }}</small></span><span class="selected-dot" v-if="symbol === s"></span>
      </button>
      <div class="side-bottom"><span class="tiny-dot good"></span> LOCAL WORKSPACE<p>Vue + FastAPI + SQLite</p><small>Observation first.<br>Every update has a record.</small></div>
    </aside>

    <main>
      <div class="page-heading"><div><div class="eyebrow">WORKSPACE <span>/</span> OVERVIEW</div><h1>Market overview<span class="heading-dot">.</span></h1><p class="subtitle">Follow the market. Inspect the evidence.</p></div><div class="status-chip" :class="{ positive: connected && mode === 'live' && age !== null && age < 60 && feed.state === 'connected' }"><span class="tiny-dot"></span>{{ statusLabel }}</div></div>
      <div v-if="error" class="error-banner" role="alert">{{ error }}</div>
      <div class="mobile-instrument"><label for="instrument">Instrument</label><select id="instrument" v-model="symbol"><option value="AAPL">AAPL · Apple Inc.</option><option value="MSFT" :disabled="dataset === 'demo'">MSFT · Microsoft</option><option value="BTC-USD" :disabled="dataset === 'demo'">BTC-USD · Bitcoin</option></select></div>
      <div class="mode-bar"><div class="segmented"><button :class="{ chosen: mode === 'live' }" @click="setMode('live')"><span class="tiny-dot"></span>Yahoo live</button><button :class="{ chosen: mode === 'replay' && dataset === 'live' }" @click="setMode('replay')">↶ Saved Yahoo</button><button :class="{ chosen: dataset === 'demo' }" @click="setMode('replay', 'demo')">Demo replay</button></div><span class="mode-note">{{ dataset === 'demo' ? 'CONSTRUCTED TEACHING DATA' : mode === 'replay' ? 'READ-ONLY RECORDING' : 'YAHOO FINANCE · WEBSOCKET' }}</span></div>

      <div class="metrics">
        <div class="metric"><span>LAST OBSERVED PRICE</span><div>{{ latest ? '$' + format(latest.price) : '—' }}<small>{{ symbol }}</small></div><p :class="change >= 0 ? 'green' : 'red'">{{ change == null ? 'Waiting for source data' : (change >= 0 ? '+' : '') + format(change) + ' (' + format(change / bars[0].open * 100) + '%) in captured range' }}</p></div>
        <div class="metric"><span>{{ mode === 'replay' ? 'AGE AT REPLAY CLOCK' : 'SOURCE OBSERVATION AGE' }}</span><div class="medium-value">{{ ageText }}</div><p>{{ mode === 'replay' ? 'Historical clock, not current data' : 'Measured from provider timestamp' }}</p></div>
        <div class="metric"><span>STORED OBSERVATIONS</span><div>{{ format(stats.observations, 0) }}<small>unique</small></div><p>{{ format(stats.deliveries, 0) }} receipts · {{ stats.duplicates }} exact repeats</p></div>
        <div class="metric"><span>CURRENT BAR</span><div class="medium-value">{{ !last ? 'No candle' : last.complete ? 'Complete' : 'Forming' }}<span v-if="last" class="bar-dot" :class="{ complete: last.complete }"></span></div><p>{{ interval }} interval · {{ bars.length }} observed bars</p></div>
      </div>

      <div class="workspace-grid">
        <section class="chart-card">
          <div class="chart-toolbar"><div class="instrument"><span class="ticker-icon">{{ symbol === 'BTC-USD' ? '₿' : symbol[0] }}</span><div><strong>{{ symbol }} <span class="muted">/ USD</span></strong><small>{{ names[symbol] }}</small></div></div><div class="timeframes"><button v-for="i in ['1m','5m','15m','1h','1d']" :key="i" :class="{ chosen: interval === i }" @click="interval = i">{{ i }}</button><button class="fit-button" title="Fit all observed candles" aria-label="Fit chart" @click="chart.timeScale().fitContent()">⛶</button></div></div>
          <div class="chart-legend"><span class="legend-mode">{{ mode === 'replay' ? 'REPLAY' : 'CANDLES' }}</span><span v-for="[key,label] in [['open','O'],['high','H'],['low','L'],['close','C']]" :key="key">{{ label }} <b :class="selected && selected.close >= selected.open ? 'green' : 'red'">{{ format(selected?.[key]) }}</b></span><span>VOL <b>{{ format(selected?.volume, 0) }}</b></span></div>
          <div class="chart-wrap"><div ref="chartEl" class="chart" aria-label="Candlestick price and volume chart"></div><div v-if="!bars.length" class="empty-chart"><span class="empty-icon">⌁</span><h3>{{ mode === 'replay' && data?.total ? 'Your recording is ready' : mode === 'replay' ? 'No recorded observations' : 'Waiting for market observations' }}</h3><p>{{ mode === 'replay' && data?.total ? 'Press play or step through one receipt at a time.' : mode === 'replay' ? 'Choose another symbol or time range, or try Demo replay.' : 'Yahoo updates will appear here as they arrive.' }}</p><button v-if="mode === 'live'" class="text-button" @click="setMode('replay', 'demo')">Explore demo replay →</button></div></div>
          <div class="chart-footer"><span><span class="tiny-dot" :class="{ good: connected }"></span> {{ connected ? 'Backend WebSocket connected' : 'Backend WebSocket offline' }}</span><span>All chart times UTC · {{ dataset === 'demo' ? 'Synthetic data' : 'Captured ticks only' }}</span></div>
        </section>

        <aside class="details-column">
          <section class="panel provenance"><div class="panel-title">Data provenance <span>↗</span></div><div class="source-label">{{ dataset === 'demo' ? 'DEMO DATASET' : 'MARKET DATA SOURCE' }}</div><h3>{{ dataset === 'demo' ? 'Teaching fixture' : 'Yahoo Finance' }}</h3><p>{{ dataset === 'demo' ? 'Made-up prices for repeatable testing. These are not AAPL market quotes.' : 'Observed streaming quotes. Availability and timing depend on the instrument and provider.' }}</p><dl><dt>Upstream</dt><dd>{{ feed.state }}</dd><dt>Source time</dt><dd>{{ shortTime(latest?.source_time) }}</dd><dt>Receipt time</dt><dd>{{ shortTime(data?.last_receipt_time) }}</dd><dt>Storage</dt><dd>SQLite · persistent</dd></dl><button class="outline-button" :disabled="busy" @click="toggleFeed">{{ ['connected','connecting'].includes(feed.state) ? 'Disconnect Yahoo' : 'Connect Yahoo' }}</button><p class="feed-detail">{{ feed.detail }}</p></section>
          <section class="panel"><div class="panel-title">Candle inspector <span>⌖</span></div><p class="inspect-time">{{ stamp(selected?.timestamp) }}</p><dl><dt>Bar state</dt><dd :class="selected?.complete ? 'green' : 'amber'">{{ selected ? selected.complete ? 'Complete' : 'Forming' : '—' }}</dd><dt>High / low</dt><dd>{{ format(selected?.high) }} / {{ format(selected?.low) }}</dd><dt>Observations</dt><dd>{{ selected?.observations ?? '—' }}</dd><dt>Volume</dt><dd>{{ selected?.volume == null ? 'Unknown' : format(selected.volume, 0) }}</dd></dl><div class="info-note">Volume is the change in a session total. A missing baseline or reset makes it unknown. Crypto rolling volume is not candle volume.</div></section>
        </aside>

        <section v-if="mode === 'replay'" class="panel replay-panel"><div class="replay-header"><div><div class="panel-title">Receipt-order replay <span class="pill">READ ONLY</span></div><p>Rebuild candles in arrival order, including duplicates, revisions, and late observations.</p></div><span class="replay-count">{{ data?.cursor || 0 }} / {{ data?.total || 0 }} receipts</span></div><div class="replay-controls"><button class="play-button" :disabled="!data?.total" @click="command(data?.playing ? 'pause' : 'play')">{{ data?.playing ? 'Ⅱ Pause' : '▶ Play' }}</button><button class="outline-button" :disabled="!data?.total" @click="command('step')">Step →</button><button class="icon-button" title="Reset replay" aria-label="Reset replay" @click="command('reset')">↶</button><input aria-label="Replay position" type="range" min="0" :max="data?.total || 0" :value="data?.cursor || 0" @input="command('seek', { cursor: Number($event.target.value) })"><select aria-label="Replay speed" v-model="speed" @change="command('speed', { batch: Number(speed) })"><option :value="1">1 receipt / tick</option><option :value="10">10 receipts / tick</option><option :value="50">50 receipts / tick</option></select></div><form class="range-form" @submit.prevent="openStream"><label>From receipt time (UTC)<input type="datetime-local" step="1" v-model="start"></label><label>To receipt time (UTC)<input type="datetime-local" step="1" v-model="end"></label><button class="outline-button" type="submit">Load range</button><span>{{ rangeSessions.length ? stamp(rangeSessions[0].start) + ' — ' + stamp(rangeSessions[0].end) : 'No saved session for this instrument.' }}</span></form><div class="replay-clock">Replay clock <b>{{ stamp(data?.clock) }}</b></div></section>

        <section class="panel audit-panel"><div class="audit-heading"><div class="panel-title">Observation ledger <span class="pill">{{ dataset.toUpperCase() }}</span></div><span class="muted">Latest 12 receipts · immutable source records</span></div><div class="table-wrap"><table><thead><tr><th>RECEIPT / OBS.</th><th>SOURCE TIME · UTC</th><th>RECEIVED · UTC</th><th class="numeric">PRICE</th><th class="numeric">SOURCE VOLUME</th><th>EVENT</th></tr></thead><tbody><tr v-for="r in data?.audit || []" :key="r.receipt_id"><td>#{{ r.receipt_id }} <span class="muted">/ {{ r.id }}</span></td><td>{{ shortTime(r.source_time) }}</td><td>{{ shortTime(r.receipt_time) }}</td><td class="numeric">{{ format(r.price) }}</td><td class="numeric">{{ format(r.cumulative_volume, 0) }}</td><td><span class="event-pill" :class="{ repeat: r.duplicate }">{{ r.duplicate ? 'Exact repeat' : r.revision != null ? 'Revision ' + r.revision : 'Observation' }}</span></td></tr><tr v-if="!data?.audit?.length"><td colspan="6" class="empty-ledger">No receipts in this view. Live observations are saved automatically.</td></tr></tbody></table></div></section>
      </div>
      <footer class="page-footer"><span>IST 402 · LIVE MARKET WORKSTATION <b>PART 4.1</b></span><span>Educational observation tool · No orders placed · Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView Lightweight Charts™</a></span></footer>
    </main>
  </div>
</template>
