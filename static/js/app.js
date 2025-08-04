// Import the io function from socket.io-client
import { io } from "socket.io-client"

class RemoteDesktopClient {
  constructor() {
    this.socket = io()
    this.selectedClient = null
    this.streaming = false
    this.clients = {}

    this.initializeElements()
    this.setupEventListeners()
    this.setupSocketEvents()
  }

  initializeElements() {
    // Status elements
    this.connectionStatus = document.getElementById("connection-status")
    this.clientsCount = document.getElementById("clients-count")

    // Client list
    this.clientsList = document.getElementById("clients-list")

    // Panels
    this.noClientSelected = document.getElementById("no-client-selected")
    this.clientPanel = document.getElementById("client-panel")

    // Controls
    this.toggleStreamBtn = document.getElementById("toggle-stream")
    this.frameDelaySlider = document.getElementById("frame-delay")
    this.delayValue = document.getElementById("delay-value")
    this.directoryPath = document.getElementById("directory-path")
    this.browseDirectoryBtn = document.getElementById("browse-directory")
    this.terminalInput = document.getElementById("terminal-input")
    this.sendCommandBtn = document.getElementById("send-command")

    // Viewer
    this.screenCanvas = document.getElementById("screen-canvas")
    this.screenCtx = this.screenCanvas.getContext("2d")
    this.noStream = document.getElementById("no-stream")

    // File explorer
    this.currentPath = document.getElementById("current-path")
    this.goBackBtn = document.getElementById("go-back")
    this.fileList = document.getElementById("file-list")

    // Terminal
    this.terminalOutput = document.getElementById("terminal-output")
    this.terminalCmd = document.getElementById("terminal-cmd")

    // Logs
    this.logOutput = document.getElementById("log-output")
  }

  setupEventListeners() {
    // Stream control
    this.toggleStreamBtn.addEventListener("click", () => this.toggleStream())

    // Frame delay
    this.frameDelaySlider.addEventListener("input", (e) => {
      const delay = Number.parseFloat(e.target.value)
      this.delayValue.textContent = `${delay}s`
      this.setFrameDelay(delay)
    })

    // Directory browsing
    this.browseDirectoryBtn.addEventListener("click", () => this.browseDirectory())
    this.goBackBtn.addEventListener("click", () => this.goBack())

    // Terminal
    this.sendCommandBtn.addEventListener("click", () => this.sendTerminalCommand())
    this.terminalInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") this.sendTerminalCommand()
    })
    this.terminalCmd.addEventListener("keypress", (e) => {
      if (e.key === "Enter") this.sendTerminalCommand(this.terminalCmd.value)
    })

    // Tabs
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => this.switchTab(e.target.dataset.tab))
    })

    // Canvas mouse events for remote control
    this.screenCanvas.addEventListener("click", (e) => this.handleCanvasClick(e))
    this.screenCanvas.addEventListener("contextmenu", (e) => {
      e.preventDefault()
      this.handleCanvasRightClick(e)
    })

    // Get initial clients list
    this.socket.emit("get_clients")
  }

  setupSocketEvents() {
    this.socket.on("connect", () => {
      this.connectionStatus.textContent = "Connected"
      this.connectionStatus.className = "status connected"
      this.log("Connected to server", "info")
    })

    this.socket.on("disconnect", () => {
      this.connectionStatus.textContent = "Disconnected"
      this.connectionStatus.className = "status disconnected"
      this.log("Disconnected from server", "error")
    })

    this.socket.on("client_connected", (data) => {
      this.clients[data.sid] = data.info
      this.updateClientsList()
      this.log(`Client connected: ${data.info.data?.username || "Unknown"}`, "info")
    })

    this.socket.on("clients_list", (data) => {
      this.clients = data.clients
      this.updateClientsList()
    })

    this.socket.on("video_frame", (data) => {
      if (data.client_id === this.selectedClient) {
        this.displayFrame(data.frame)
      }
    })

    this.socket.on("record_frame", (data) => {
      if (data.client_id === this.selectedClient) {
        this.displayFrame(data.frame)
      }
    })

    this.socket.on("stream_status", (data) => {
      if (data.client_id === this.selectedClient) {
        this.streaming = data.active
        this.updateStreamButton()
      }
    })

    this.socket.on("terminal_output", (data) => {
      if (data.client_id === this.selectedClient) {
        this.displayTerminalOutput(data.data)
      }
    })

    this.socket.on("file_explorer", (data) => {
      if (data.client_id === this.selectedClient) {
        this.displayFileExplorer(data.data)
      }
    })

    this.socket.on("client_info", (data) => {
      this.log(`Info: ${data.data.data?.message || "Unknown message"}`, "info")
    })

    this.socket.on("client_error", (data) => {
      this.log(`Error: ${data.data.data?.message || "Unknown error"}`, "error")
    })

    this.socket.on("client_warning", (data) => {
      this.log(`Warning: ${data.data.data?.message || "Unknown warning"}`, "warning")
    })
  }

  updateClientsList() {
    const count = Object.keys(this.clients).length
    this.clientsCount.textContent = `Clients: ${count}`

    if (count === 0) {
      this.clientsList.innerHTML = '<div class="no-clients">No clients connected</div>'
      return
    }

    this.clientsList.innerHTML = ""
    Object.entries(this.clients).forEach(([sid, info]) => {
      const clientItem = document.createElement("div")
      clientItem.className = "client-item"
      clientItem.dataset.clientId = sid

      const username = info.data?.username || "Unknown"
      const pcName = info.data?.pc_name || "Unknown PC"

      clientItem.innerHTML = `
                <div class="client-name">${username}@${pcName}</div>
                <div class="client-info">ID: ${sid.substring(0, 8)}...</div>
            `

      clientItem.addEventListener("click", () => this.selectClient(sid))
      this.clientsList.appendChild(clientItem)
    })
  }

  selectClient(clientId) {
    this.selectedClient = clientId

    // Update UI
    document.querySelectorAll(".client-item").forEach((item) => {
      item.classList.remove("active")
    })
    document.querySelector(`[data-client-id="${clientId}"]`).classList.add("active")

    this.noClientSelected.style.display = "none"
    this.clientPanel.style.display = "flex"

    this.log(`Selected client: ${clientId}`, "info")

    // Reset stream state
    this.streaming = false
    this.updateStreamButton()
  }

  toggleStream() {
    if (!this.selectedClient) return

    const enable = !this.streaming
    this.socket.emit("control_streaming", {
      client_id: this.selectedClient,
      enable: enable,
    })

    this.log(`${enable ? "Starting" : "Stopping"} stream for client ${this.selectedClient}`, "info")
  }

  updateStreamButton() {
    this.toggleStreamBtn.textContent = this.streaming ? "Stop Stream" : "Start Stream"
    this.toggleStreamBtn.className = this.streaming ? "btn btn-secondary" : "btn btn-primary"

    if (this.streaming) {
      this.noStream.style.display = "none"
    } else {
      this.noStream.style.display = "block"
    }
  }

  setFrameDelay(delay) {
    if (!this.selectedClient) return

    this.socket.emit("set_frame_delay", {
      client_id: this.selectedClient,
      delay: delay,
    })
  }

  displayFrame(frameData) {
    const img = new Image()
    img.onload = () => {
      this.screenCanvas.width = img.width
      this.screenCanvas.height = img.height
      this.screenCtx.drawImage(img, 0, 0)
    }
    img.src = `data:image/jpeg;base64,${frameData}`
  }

  handleCanvasClick(e) {
    if (!this.selectedClient || !this.streaming) return

    const rect = this.screenCanvas.getBoundingClientRect()
    const x = Math.floor((e.clientX - rect.left) * (this.screenCanvas.width / rect.width))
    const y = Math.floor((e.clientY - rect.top) * (this.screenCanvas.height / rect.height))

    this.socket.emit("desktop_control", {
      client_id: this.selectedClient,
      control_data: {
        type: "click",
        x: x,
        y: y,
        button: "left",
      },
    })
  }

  handleCanvasRightClick(e) {
    if (!this.selectedClient || !this.streaming) return

    const rect = this.screenCanvas.getBoundingClientRect()
    const x = Math.floor((e.clientX - rect.left) * (this.screenCanvas.width / rect.width))
    const y = Math.floor((e.clientY - rect.top) * (this.screenCanvas.height / rect.height))

    this.socket.emit("desktop_control", {
      client_id: this.selectedClient,
      control_data: {
        type: "click",
        x: x,
        y: y,
        button: "right",
      },
    })
  }

  browseDirectory() {
    if (!this.selectedClient) return

    const directory = this.directoryPath.value || "C:\\"
    this.socket.emit("get_directory", {
      client_id: this.selectedClient,
      directory: directory,
    })
  }

  goBack() {
    if (!this.selectedClient) return

    const currentDir = this.currentPath.textContent
    this.socket.emit("get_directory", {
      client_id: this.selectedClient,
      directory: currentDir,
      back: true,
    })
  }

  displayFileExplorer(data) {
    this.currentPath.textContent = data.data?.current_directory || "Unknown"

    if (data.data?.files) {
      this.fileList.innerHTML = ""
      data.data.files.forEach((file) => {
        const fileItem = document.createElement("div")
        fileItem.className = "file-item"

        const icon = file.is_directory ? "📁" : "📄"
        fileItem.innerHTML = `
                    <span class="file-icon">${icon}</span>
                    <span class="file-name">${file.name}</span>
                `

        if (file.is_directory) {
          fileItem.addEventListener("click", () => {
            this.directoryPath.value = file.path
            this.browseDirectory()
          })
        }

        this.fileList.appendChild(fileItem)
      })
    }
  }

  sendTerminalCommand(command = null) {
    if (!this.selectedClient) return

    const cmd = command || this.terminalInput.value || this.terminalCmd.value
    if (!cmd.trim()) return

    this.socket.emit("send_terminal_command", {
      client_id: this.selectedClient,
      command: cmd,
    })

    this.terminalInput.value = ""
    this.terminalCmd.value = ""

    // Add command to terminal output
    this.terminalOutput.innerHTML += `<div class="log-entry">$ ${cmd}</div>`
    this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight
  }

  displayTerminalOutput(data) {
    const stdout = data.stdout || ""
    const stderr = data.stderr || ""

    if (stdout) {
      this.terminalOutput.innerHTML += `<div class="log-entry">${stdout}</div>`
    }
    if (stderr) {
      this.terminalOutput.innerHTML += `<div class="log-entry error">${stderr}</div>`
    }

    this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight
  }

  switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.remove("active")
    })
    document.querySelector(`[data-tab="${tabName}"]`).classList.add("active")

    // Update tab panels
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.remove("active")
    })
    document.getElementById(`${tabName}-tab`).classList.add("active")
  }

  log(message, type = "info") {
    const timestamp = new Date().toLocaleTimeString()
    const logEntry = document.createElement("div")
    logEntry.className = `log-entry ${type}`
    logEntry.textContent = `[${timestamp}] ${message}`

    this.logOutput.appendChild(logEntry)
    this.logOutput.scrollTop = this.logOutput.scrollHeight

    // Keep only last 100 log entries
    while (this.logOutput.children.length > 100) {
      this.logOutput.removeChild(this.logOutput.firstChild)
    }
  }
}

// Initialize the application
document.addEventListener("DOMContentLoaded", () => {
  new RemoteDesktopClient()
})
