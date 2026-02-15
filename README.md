# Bluetooth Heart Rate Monitor (蓝牙心率监测器)

这是一个基于 Web 的实时蓝牙心率监测应用，使用 Python FastAPI 作为后端，Bleak 处理蓝牙连接，前端采用 Tailwind CSS 和 Chart.js 进行数据可视化。

## ✨ 主要功能

- **实时心率监测**：通过蓝牙低功耗 (BLE) 连接心率带或手环，实时显示 BPM。
- **动态心电图模拟**：基于实时心率生成模拟的心电图 (ECG) 动画。
- **历史数据记录**：
  - 使用 SQLite 数据库自动存储心率数据。
  - 支持按 **原始数据**、**分钟平均**、**小时平均**、**天平均** 查看历史趋势。
  - 交互式图表，支持平滑曲线和渐变效果。
- **多语言支持**：
  - 支持 **简体中文**、**繁体中文** 和 **English**。
  - 自动检测系统语言，也可手动切换。
- **深色模式支持**：
  - 支持 **浅色 (Light)**、**深色 (Dark)** 和 **自动 (跟随系统)** 模式。
- **设备扫描与管理**：
  - 实时扫描附近的 BLE 设备。
  - 显示信号强度 (RSSI)。
  - 自动重连机制。

## 🛠️ 技术栈

- **后端**：Python, FastAPI, WebSocket, Bleak (Bluetooth Low Energy), SQLite
- **前端**：HTML5, JavaScript, Tailwind CSS (CDN), Chart.js (CDN)

## 📦 安装说明

1. **克隆或下载项目**

2. **安装依赖**
   确保已安装 Python 3.7+，然后运行：
   ```bash
   pip install -r requirements.txt
   ```
   *注意：如果在 Windows 上遇到路径问题，可以尝试使用 `python -m pip install -r requirements.txt`*

## 🚀 运行指南

1. **启动服务器**
   在项目根目录下运行：
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **访问应用**
   打开浏览器访问：
   - [http://localhost:8000](http://localhost:8000)
   - 或者使用本机 IP 地址在手机上访问（需在同一局域网）。

## 📝 注意事项

- **蓝牙硬件**：运行此应用的设备需要具备蓝牙功能。
- **模拟模式**：如果未检测到蓝牙适配器或未安装 `bleak`，应用将自动进入**模拟模式** (Mock Mode)，生成随机数据用于测试 UI 和功能。
- **数据库**：首次运行时会自动在根目录创建 `heart_rate.db` 文件用于存储历史数据。

## 📂 项目结构

- `main.py`: 后端核心逻辑，包含 FastAPI 应用、WebSocket 处理、蓝牙连接和数据库操作。
- `templates/index.html`: 前端页面，包含 UI 布局、图表逻辑和交互脚本。
- `static/`: 静态资源文件。
- `requirements.txt`: Python 依赖列表。
