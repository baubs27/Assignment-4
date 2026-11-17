import { test, expect } from '@playwright/test'

test.beforeEach(async({page})=>{
  // Fonts are optional; CI browser checks must not depend on any external website.
  await page.route('**/*',route=>route.request().url().startsWith('http://127.0.0.1:8765/')?route.continue():route.abort())
})

test('completed and provisional SMAs update in the real replay chart',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message))
  await page.goto('/')
  await page.getByRole('button',{name:'Demo replay',exact:true}).click()
  await expect(page.getByLabel('Replay position')).toHaveAttribute('max','276')
  await page.getByLabel('Replay position').press('End')
  await expect(page.getByText('276 / 276 receipts',{exact:true})).toBeVisible()
  await page.getByLabel('Fast SMA window').fill('2')
  await page.getByLabel('Slow SMA window').fill('3')
  await page.mouse.move(5,5) // Read the latest candle, rather than a crosshair-selected historical candle.
  // Last forming close 102.50, previous completed closes 101.22 and 100.91.
  await expect(page.getByTestId('chart-sma')).toHaveText('101.8600 / 101.5433')
  await expect(page.getByText(/Provisional · no trading decision/)).toBeVisible()
  expect(errors).toEqual([])
})

test('backtest account and ledgers agree with persisted result and survive reload',async({page,request})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message))
  await page.goto('/')
  await page.getByRole('button',{name:'Strategy & backtests',exact:true}).click()
  await page.getByLabel('Strategy fast SMA').fill('2')
  await page.getByLabel('Strategy slow SMA').fill('3')
  await page.getByLabel('Initial cash',{exact:true}).fill('1000')
  await page.getByLabel('Order quantity',{exact:true}).fill('4')
  const saved=page.waitForResponse(r=>r.url().endsWith('/api/research/backtest')&&r.request().method()==='POST')
  await page.getByRole('button',{name:'Run backtest',exact:true}).click()
  const response=await saved;expect(response.status()).toBe(200)
  const run=await response.json()
  expect(run.result.fills.length).toBeGreaterThan(0)
  await expect(page.getByTestId('account-summary')).toContainText(run.result.account.equity.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}))
  await expect(page.getByTestId('fills-table').locator('tbody tr')).toHaveCount(run.result.fills.length)
  await page.getByRole('button',{name:/Indicator decisions/}).click()
  const rows=page.getByTestId('decisions-table').locator('tbody tr')
  await expect(rows).toHaveCount(run.result.decisions.length)
  const known=run.result.decisions[2]
  await expect(rows.nth(2)).toContainText(known.fast.toFixed(4))
  await expect(rows.nth(2)).toContainText(known.slow.toFixed(4))
  await page.reload();await page.getByRole('button',{name:'Strategy & backtests',exact:true}).click()
  await page.getByLabel('Saved run',{exact:true}).selectOption(run.id)
  await expect(page.getByTestId('account-summary')).toContainText('1,000.00')
  const persisted=await (await request.get('/api/research/runs/'+run.id)).json()
  expect(persisted.result).toEqual(run.result)
  expect(errors).toEqual([])
  if(process.env.E2E_EVIDENCE==='1') await page.screenshot({path:'../test-results/part4-2-demo-backtest.png',fullPage:true})
})

test('paper account starts and pauses safely and source errors are understandable',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Strategy & backtests',exact:true}).click()
  await page.getByLabel('Backtest source').selectOption('recorded')
  await page.getByRole('button',{name:'Start live paper account',exact:true}).click()
  await expect(page.getByRole('button',{name:'Pause paper account',exact:true})).toBeVisible()
  await expect(page.getByTestId('account-summary')).toContainText('0 fills')
  await page.getByRole('button',{name:'Pause paper account',exact:true}).click()
  await expect(page.getByRole('button',{name:'Resume paper account',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Run backtest',exact:true}).click()
  await expect(page.getByRole('alert')).toContainText('No completed candles')
})

test('strategy lab and market chart remain usable on narrow screens',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/')
  await expect(page.getByLabel('Instrument',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Strategy & backtests',exact:true}).click()
  await expect(page.getByRole('button',{name:'Run backtest',exact:true})).toBeVisible()
  const widths=await page.evaluate(()=>({page:document.documentElement.scrollWidth,viewport:innerWidth}))
  expect(widths.page).toBeLessThanOrEqual(widths.viewport)
})
