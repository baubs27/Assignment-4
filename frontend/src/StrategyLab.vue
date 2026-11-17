<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import ResearchChart from './ResearchChart.vue'
const props=defineProps({symbol:String,interval:String,fast:Number,slow:Number})
const params=ref({symbol:props.symbol||'AAPL',interval:props.interval||'1m',source:'demo',fast:props.fast||5,slow:props.slow||20,
  cash:10000,quantity:10,fee:0,slippage_bps:0,history_id:null})
const start=ref(''),end=ref(''),period=ref('1y'),run=ref(null),runs=ref([]),history=ref([]),busy=ref(false),error=ref(''),message=ref('')
const tab=ref('fills')
let poll
watch(()=>params.value.source,(source)=>{
  if(source==='history') params.value.interval='1d'
})
const account=computed(()=>run.value?.result.account)
const compatibleHistory=computed(()=>history.value.filter(h=>h.symbol===params.value.symbol))
const decisions=computed(()=>run.value?.result.decisions||[])
const last=computed(()=>decisions.value.at(-1))
const fmt=(n,d=2)=>n==null?'—':Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d})
const date=t=>t==null?'—':new Date(t*1000).toISOString().replace('T',' ').slice(0,19)+' UTC'
async function api(path,body) {
  const r=await fetch('/api/research'+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined)
  const data=await r.json()
  if(!r.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail))
  return data
}
async function refresh() {
  try { runs.value=(await api('/runs')).runs;history.value=(await api('/history')).history }
  catch(e) { error.value=e.message }
}
function body() {
  return {...params.value,start:start.value?new Date(start.value+'Z').getTime()/1000:null,
    end:end.value?new Date(end.value+'Z').getTime()/1000:null}
}
async function execute(kind) {
  busy.value=true;error.value='';message.value=''
  try {
    run.value=await api('/'+kind,body())
    message.value=kind==='paper'?'Paper account started. Existing candles warm up the SMAs; only future completed bars can place orders.':'Backtest saved with a frozen source fingerprint.'
    await refresh()
  } catch(e) { error.value=e.message }
  finally { busy.value=false }
}
async function download() {
  busy.value=true;error.value=''
  try {
    const h=await api('/history',{symbol:params.value.symbol,period:period.value})
    await refresh();params.value.history_id=h.id;params.value.source='history'
    message.value=`Saved ${h.bars} completed daily Yahoo bars. Today's candle is excluded.`
  } catch(e) {error.value=e.message} finally {busy.value=false}
}
async function load(id,syncParameters=true) {
  error.value=''
  try {
    run.value=await api('/runs/'+id)
    if(syncParameters){
      params.value={...run.value.config}
      start.value=params.value.start==null?'':new Date(params.value.start*1000).toISOString().slice(0,19)
      end.value=params.value.end==null?'':new Date(params.value.end*1000).toISOString().slice(0,19)
    }
  } catch(e) { error.value=e.message }
}
async function pause() {
  try { run.value=await api('/paper/'+run.value.id+'/pause',{});await refresh() }
  catch(e) {error.value=e.message}
}
async function resume() {
  try { run.value=await api('/paper/'+run.value.id+'/resume',{});await refresh() }
  catch(e) {error.value=e.message}
}
onMounted(()=>{
  refresh()
  poll=setInterval(async()=>{if(run.value?.kind==='paper'&&run.value.status==='active') await load(run.value.id,false)},1500)
})
onBeforeUnmount(()=>clearInterval(poll))
</script>
<template>
  <section class="strategy-lab">
    <div class="lab-intro"><div><div class="eyebrow">OBSERVE → SIGNAL → SIMULATE → REVIEW</div><h2>Strategy lab</h2><p>One crossover strategy. An inspectable account. A recorded result.</p></div><span class="pill">SIMULATED FUNDS ONLY</span></div>
    <div v-if="error" class="error-banner" role="alert">{{ error }}</div>
    <div v-if="message" class="success-banner" role="status">{{ message }}</div>
    <form class="panel lab-form" @submit.prevent="execute('backtest')">
      <div class="lab-form-grid">
        <label>Instrument<select v-model="params.symbol" aria-label="Strategy instrument" @change="params.history_id=null"><option>AAPL</option><option>MSFT</option><option>BTC-USD</option></select></label>
        <label>Historical source<select v-model="params.source" aria-label="Backtest source"><option value="demo">Constructed demo recording</option><option value="recorded">Saved Yahoo observations</option><option value="history">Downloaded Yahoo daily history</option></select></label>
        <label>Interval<select v-model="params.interval" aria-label="Strategy interval" :disabled="params.source==='history'"><option v-for="i in ['1m','5m','15m','1h','1d']" :key="i">{{i}}</option></select></label>
        <label>Fast SMA<input type="number" v-model.number="params.fast" min="1" max="499" aria-label="Strategy fast SMA" required></label>
        <label>Slow SMA<input type="number" v-model.number="params.slow" min="2" max="500" aria-label="Strategy slow SMA" required></label>
        <label>Initial cash ($)<input type="number" v-model.number="params.cash" min="1" max="1000000000" step="0.01" aria-label="Initial cash" required></label>
        <label>Buy quantity (units)<input type="number" v-model.number="params.quantity" min="1" max="1000000" aria-label="Order quantity" required></label>
        <label>Fee per fill ($)<input type="number" v-model.number="params.fee" min="0" max="1000" step="0.01" aria-label="Fee per fill" required></label>
        <label>Adverse slippage (bps)<input type="number" v-model.number="params.slippage_bps" min="0" max="1000" step="0.1" aria-label="Slippage basis points" required></label>
      </div>
      <div class="history-import"><span>Real daily history</span><select aria-label="History period" v-model="period"><option v-for="p in ['1mo','3mo','6mo','1y','2y']" :key="p">{{p}}</option></select><button type="button" class="outline-button" @click="download" :disabled="busy">Fetch Yahoo history</button><small>Separate from the required Yahoo streaming feed. Downloads are frozen and unadjusted.</small></div>
      <label v-if="params.source==='history'" class="download-selection">Saved historical download<select v-model="params.history_id" aria-label="Historical download" required><option :value="null" disabled>Fetch or choose a daily dataset</option><option v-for="h in compatibleHistory" :key="h.id" :value="h.id">{{h.bars}} bars · {{date(h.fetched_at)}}</option></select></label>
      <div class="lab-range"><label>{{params.source==='history'?'From bar date':'From receipt time'}} (UTC)<input type="datetime-local" v-model="start" aria-label="Backtest start" step="1"></label><label>{{params.source==='history'?'To bar date':'To receipt time'}} (UTC)<input type="datetime-local" v-model="end" aria-label="Backtest end" step="1"></label><span>Optional. Blank selects the complete saved sample. Warm-up uses this selection only.</span></div>
      <div class="lab-actions"><button class="play-button" type="submit" :disabled="busy">{{busy?'Working…':'Run backtest'}}</button><button class="outline-button" type="button" @click="execute('paper')" :disabled="busy||params.source!=='recorded'">Start live paper account</button><small>Paper mode uses future Yahoo observations. No real orders are sent.</small></div>
    </form>
    <div class="lab-assumptions"><strong>Execution rules</strong><span>Long only · fixed buy size · sell the full position on a downward crossover · no borrowing or shorting.</span><span>Completed candles only. Daily history fills at the next open; recorded/live ticks fill after the decision at the next eligible observed price. Fees enter cost basis. Open positions are marked, not forcibly sold at the end.</span></div>
    <div class="saved-runs"><label>Saved experiment or paper account<select aria-label="Saved run" :value="run?.id||''" @change="load($event.target.value)"><option value="" disabled>Select a saved run</option><option v-for="r in runs" :value="r.id" :key="r.id">{{r.kind}} · {{r.config.symbol}} · SMA {{r.config.fast}}/{{r.config.slow}} · {{r.status}} · {{date(r.created_at)}}</option></select></label><button class="outline-button" @click="refresh">Refresh runs</button></div>
    <template v-if="run">
      <div class="run-heading"><div><h3>{{run.kind==='paper'?'Paper account':'Historical backtest'}} <span class="pill">{{run.status.toUpperCase()}}</span></h3><p>{{run.source.label}} · {{run.config.symbol}} · {{run.config.interval}} · SMA {{run.config.fast}} / {{run.config.slow}}</p><p>{{run.source.execution}}</p></div><button v-if="run.kind==='paper'&&run.status==='active'" class="outline-button" @click="pause">Pause paper account</button><button v-else-if="run.kind==='paper'" class="outline-button" @click="resume">Resume paper account</button></div>
      <div class="account-grid" data-testid="account-summary">
        <div><span>ACCOUNT EQUITY</span><strong>${{fmt(account.equity)}}</strong><small :class="account.total_pnl>=0?'green':'red'">{{fmt(account.return_pct)}}% return</small></div>
        <div><span>CASH</span><strong>${{fmt(account.cash)}}</strong><small>Start ${{fmt(account.initial_cash)}}</small></div>
        <div><span>POSITION</span><strong>{{fmt(account.quantity,0)}} units</strong><small>Average cost ${{fmt(account.average_cost,4)}}</small></div>
        <div><span>REALIZED / UNREALIZED</span><strong>${{fmt(account.realized_pnl)}} / ${{fmt(account.unrealized_pnl)}}</strong><small>Fees ${{fmt(account.fees)}}</small></div>
        <div><span>MAX DRAWDOWN</span><strong>{{fmt(account.max_drawdown_pct)}}%</strong><small>{{account.fills}} fills · {{account.pending_orders}} pending orders</small></div>
      </div>
      <section class="panel run-chart-panel"><div class="panel-title">Decision-time candles & account equity <span class="muted">Fast SMA cyan · Slow SMA gold</span></div><p>Chart uses candles frozen when each decision was made. Later revisions do not rewrite executed decisions.</p><ResearchChart :result="run.result" /></section>
      <div class="run-caption"><span>Latest confirmed SMA: <b data-testid="confirmed-sma">{{fmt(last?.fast,4)}} / {{fmt(last?.slow,4)}}</b></span><span>Result ID <code>{{run.id}}</code></span><span v-if="run.source.digest" :title="run.source.digest">Frozen input SHA-256 <code>{{run.source.digest.slice(0,16)}}…</code></span></div>
      <section class="panel run-ledger"><div class="ledger-tabs"><button v-for="t in ['fills','orders','decisions']" :key="t" :class="{chosen:tab===t}" @click="tab=t">{{t==='fills'?'Trade fills':t==='orders'?'Order history':'Indicator decisions'}} ({{run.result[t].length}})</button></div>
        <div class="table-wrap" v-if="tab==='fills'"><table data-testid="fills-table"><thead><tr><th>TIME · UTC</th><th>SIDE</th><th>QUANTITY</th><th>FILL PRICE</th><th>FEE</th><th>REALIZED P&L</th><th>ORDER</th></tr></thead><tbody><tr v-for="f in run.result.fills" :key="f.id"><td>{{date(f.timestamp)}}</td><td :class="f.side==='buy'?'green':'red'">{{f.side.toUpperCase()}}</td><td>{{f.quantity}}</td><td>${{fmt(f.price,4)}}</td><td>${{fmt(f.fee)}}</td><td>${{fmt(f.realized_pnl)}}</td><td>#{{f.order_id}}</td></tr><tr v-if="!run.result.fills.length"><td colspan="7" class="empty-ledger">No fills. Warm-up, flat signals, pending execution, or insufficient cash can produce no trades.</td></tr></tbody></table></div>
        <div class="table-wrap" v-if="tab==='orders'"><table><thead><tr><th>ORDER</th><th>SIDE / UNITS</th><th>SUBMITTED</th><th>ELIGIBLE AFTER</th><th>STATUS</th><th>REASON</th></tr></thead><tbody><tr v-for="o in run.result.orders" :key="o.id"><td>#{{o.id}}</td><td>{{o.side}} / {{o.quantity}}</td><td>{{date(o.submitted_at)}}</td><td>{{date(o.eligible_at)}}</td><td>{{o.status}}</td><td>{{o.reason}}</td></tr><tr v-if="!run.result.orders.length"><td colspan="6" class="empty-ledger">No orders have been generated.</td></tr></tbody></table></div>
        <div class="table-wrap" v-if="tab==='decisions'"><table data-testid="decisions-table"><thead><tr><th>CANDLE · UTC</th><th>CLOSE</th><th>FAST SMA</th><th>SLOW SMA</th><th>CROSSOVER</th><th>KNOWN AT</th></tr></thead><tbody><tr v-for="d in run.result.decisions" :key="d.timestamp"><td>{{date(d.timestamp)}}</td><td>{{fmt(d.close,4)}}</td><td>{{fmt(d.fast,4)}}</td><td>{{fmt(d.slow,4)}}</td><td>{{d.crossover||'—'}}</td><td>{{date(d.known_at)}}</td></tr></tbody></table></div>
      </section>
    </template>
    <div v-else class="lab-empty panel"><h3>Turn a strategy into an accountable result.</h3><p>Start with the constructed demo to inspect the calculations, or fetch actual Yahoo daily bars for a historical test. Every run starts a fresh simulated account and saves its parameters, orders, fills, and equity.</p></div>
    <div class="research-limits"><strong>What this result establishes</strong><p>It measures the configured rule on this selected sample under the stated fill model. It does not establish future profitability. Selecting only current symbols leaves survivorship bias; repeatedly tuning the same sample risks overfitting. Historical downloads are today's data vintage and may include later vendor corrections. Unadjusted price returns omit dividends and can be distorted by corporate actions. Quotes do not model spreads, depth, or guaranteed fills; fees/slippage only approximate costs.</p></div>
  </section>
</template>
