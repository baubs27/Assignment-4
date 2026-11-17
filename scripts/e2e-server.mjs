import { spawn } from 'node:child_process'
import { mkdtempSync, mkdirSync, existsSync, readFileSync } from 'node:fs'
import { resolve, dirname, delimiter } from 'node:path'
import { fileURLToPath } from 'node:url'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..')
mkdirSync(resolve(root,'.runtime'),{recursive:true})
const scratch=mkdtempSync(resolve(root,'.runtime/e2e-'))
const saved=resolve(root,'.runtime/python-executable.txt')
const python=process.env.MARKET_PYTHON||(existsSync(saved)?readFileSync(saved,'utf8').trim():'python')
const env={...process.env,PYTHONPATH:[resolve(root,'.runtime/python'),root].join(delimiter),
  MARKET_DB:resolve(scratch,'browser.sqlite3'),MARKET_LIVE:'0',PYTHONUNBUFFERED:'1'}
const child=spawn(python,['-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8765','--no-access-log'],{cwd:root,env,stdio:'inherit',windowsHide:true})
let stopping=false
function stop(){if(stopping)return;stopping=true;child.kill('SIGTERM')}
process.on('SIGINT',stop);process.on('SIGTERM',stop)
child.on('error',e=>{process.stderr.write(String(e));process.exit(1)})
child.on('exit',code=>process.exit(stopping?0:code||0))
