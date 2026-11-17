import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir:'./e2e',workers:1,timeout:30000,expect:{timeout:10000},
  reporter:[['list']],outputDir:'../test-results',
  use:{baseURL:'http://127.0.0.1:8765',headless:true,viewport:{width:1440,height:1000},
    channel:process.env.E2E_BROWSER_CHANNEL||undefined,screenshot:'only-on-failure',trace:'retain-on-failure'},
  webServer:{command:'node ../scripts/e2e-server.mjs',url:'http://127.0.0.1:8765/api/health',
    reuseExistingServer:false,timeout:60000,stdout:'pipe',stderr:'pipe'}
})
