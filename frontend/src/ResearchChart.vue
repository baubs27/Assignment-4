<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { createChart, CandlestickSeries, LineSeries, createSeriesMarkers } from 'lightweight-charts'
const props = defineProps({ result:Object })
const el=ref(null)
let chart, price, fast, slow, equity, markers
function draw() {
  if (!chart || !props.result) return
  const rows=props.result.decisions
  price.setData(rows.map(c=>({time:c.timestamp,open:c.open,high:c.high,low:c.low,close:c.close})))
  fast.setData(rows.filter(c=>c.fast!=null).map(c=>({time:c.timestamp,value:c.fast})))
  slow.setData(rows.filter(c=>c.slow!=null).map(c=>({time:c.timestamp,value:c.slow})))
  markers.setMarkers(rows.filter(c=>c.crossover).map(c=>({time:c.timestamp,position:c.crossover==='buy'?'belowBar':'aboveBar',
    color:c.crossover==='buy'?'#66d7b6':'#f18c9a',shape:c.crossover==='buy'?'arrowUp':'arrowDown',text:c.crossover.toUpperCase()})))
  // Equal timestamps are coalesced only for chart display; the saved curve retains all points.
  const points=new Map(props.result.equity_curve.map(p=>[p.timestamp,{time:p.timestamp,value:p.equity}]))
  equity.setData([...points.values()].sort((a,b)=>a.time-b.time))
  chart.timeScale().fitContent()
}
onMounted(()=>{
  chart=createChart(el.value,{autoSize:true,layout:{background:{type:'solid',color:'#111923'},textColor:'#8191a6'},
    grid:{vertLines:{color:'#1b2632'},horzLines:{color:'#1b2632'}},timeScale:{timeVisible:true,borderColor:'#293646'},
    rightPriceScale:{borderColor:'#293646'}})
  price=chart.addSeries(CandlestickSeries,{upColor:'#3ac5a0',downColor:'#ed7181',borderVisible:false,wickUpColor:'#3ac5a0',wickDownColor:'#ed7181'})
  fast=chart.addSeries(LineSeries,{color:'#67cfe5',lineWidth:2,title:'Fast SMA',priceLineVisible:false,lastValueVisible:false})
  slow=chart.addSeries(LineSeries,{color:'#e7bd72',lineWidth:2,title:'Slow SMA',priceLineVisible:false,lastValueVisible:false})
  equity=chart.addSeries(LineSeries,{color:'#8ad5b9',lineWidth:2,title:'Account equity'},1)
  chart.panes()[0].setStretchFactor(3);chart.panes()[1].setStretchFactor(1)
  markers=createSeriesMarkers(price,[])
  draw()
})
watch(()=>props.result,draw,{deep:true})
onBeforeUnmount(()=>chart?.remove())
</script>
<template><div ref="el" class="research-chart" aria-label="Strategy candles, moving averages, crossover markers and account equity chart"></div></template>
