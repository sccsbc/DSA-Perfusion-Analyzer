/**
 * Electron 主进程（ESM）：启动 Python FastAPI 后端，加载前端页面。
 *
 * npm run dev:electron    开发模式（Vite dev server + Electron）
 * npm run build:electron  生产打包（macOS arm64 / Windows x64）
 */
import { app, BrowserWindow, dialog } from 'electron'
import { spawn } from 'child_process'
import { createRequire } from 'module'
import path from 'path'
import http from 'http'
import fs from 'fs'
import { fileURLToPath } from 'url'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

const BACKEND_PORT = 18000

let mainWindow = null
let pythonProcess = null

function getPythonPath() {
  if (app.isPackaged) {
    const ext = process.platform === 'win32' ? '.exe' : ''
    const bundled = path.join(process.resourcesPath, 'backend', `dsa-backend${ext}`)
    if (fs.existsSync(bundled)) return bundled
  }
  return process.platform === 'win32' ? 'python' : 'python3'
}

function startBackend() {
  const pythonPath = getPythonPath()
  const cwd = app.isPackaged
    ? path.join(process.resourcesPath, 'backend')
    : path.join(__dirname, '..', '..', 'backend')

  const args = app.isPackaged
    ? [] // PyInstaller 可执行文件直接运行
    : ['-m', 'uvicorn', 'src.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)]

  console.log(`Starting backend: ${pythonPath} ${args.join(' ')} (cwd: ${cwd})`)

  pythonProcess = spawn(pythonPath, args, {
    cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  pythonProcess.stdout.on('data', (data) => console.log(`[backend] ${data}`))
  pythonProcess.stderr.on('data', (data) => console.error(`[backend] ${data}`))
  pythonProcess.on('close', (code) => console.log(`Backend exited with code ${code}`))
}

function waitForBackend(maxRetries = 30) {
  return new Promise((resolve, reject) => {
    let retries = 0
    const check = () => {
      http.get(`http://127.0.0.1:${BACKEND_PORT}/api/health`, (res) => {
        if (res.statusCode === 200) resolve()
        else if (++retries < maxRetries) setTimeout(check, 1000)
        else reject(new Error('Backend failed to start'))
      }).on('error', () => {
        if (++retries < maxRetries) setTimeout(check, 1000)
        else reject(new Error('Backend failed to start'))
      })
    }
    check()
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: 'DSA 灌注分析系统',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  if (!app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.on('closed', () => { mainWindow = null })
}

app.whenReady().then(async () => {
  startBackend()
  try {
    await waitForBackend()
    console.log('Backend ready')
  } catch (err) {
    dialog.showErrorBox('启动失败', `后端服务无法启动: ${err.message}`)
    app.quit()
    return
  }
  createWindow()
})

app.on('window-all-closed', () => {
  if (pythonProcess) { pythonProcess.kill(); pythonProcess = null }
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

app.on('before-quit', () => {
  if (pythonProcess) { pythonProcess.kill(); pythonProcess = null }
})
