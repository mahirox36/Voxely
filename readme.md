# 🎮 Voxely

> 🌟 A delightful Minecraft server manager with a modern web interface!

## ✨ Introduction

Voxely is your friendly companion for hosting and managing Minecraft servers on your local machine! Built with Python and a sleek Next.js frontend, it makes running Minecraft servers as easy as pie! 🥧

## 🚀 Features

- 🎯 **Easy Server Management**
  - Start, stop, and restart servers with a single click
  - Real-time server console with command support
  - Monitor CPU, memory usage, and player count
  - Multiple server instances support
- 📊 **Server Details**
  - Live server status and performance monitoring
  - Player management with whitelist support
  - Connection information (private & public IPs)
  - Server logs viewer (in progress)
- 🔧 **Advanced Features**
  - File manager for easy configuration
  - Plugin management system
  - Automated backups (in progress)
  - Server settings customization (in progress)
  - Players management
  - Config Editor
  - Multiple server types support (Paper, Vanilla, Fabric)
- 🎨 **Modern Web Interface**
  - Beautiful, responsive design
  - Real-time updates
  - Dark mode interface

## 🛠️ Requirements

- 🖥️ **Operating System**: Windows, Linux, or MacOS
- ☕ **Java**: Java 17 or higher
- 🐍 **Python**: Python 3.12 or higher
- 🌐 **Node.js**: v18 or higher (for the web interface)
- 🐳 **Docker & Docker Compose** (optional but recommended)

## 📦 Installation (Docker Method)

This is the easiest way! Everything will be built **locally on the user's machine**, no prebuilt images required.

1. Clone the repository:

   ```bash
   git clone https://github.com/mahirox36/Voxely.git
   cd Voxely
   ```

2. Build and start the backend + frontend containers:

   ```bash
   docker compose up --build -d
   ```

3. Check if containers are running:

   ```bash
   docker compose ps
   ```

4. Stop everything when done:

   ```bash
   docker compose down
   ```

✅ All images are built locally on the user's PC, and both services will run together seamlessly.

---

## 📦 Installation (Manual / Separate Process)

If Docker is not available:

1. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Install frontend dependencies and build:

   ```bash
   cd frontend
   npm install
   npm run build
   ```

3. Start backend and frontend separately:

   ```bash
   # Backend (in backend folder)
   python -m uvicorn core:app --port 25401

   # Frontend (in frontend folder)
   npm run start
   ```

---

## 🎮 Usage

1. Access the web interface at `http://localhost:3000`
2. Log in with root and the custom password generated in `backend/.env`
3. Create a new server or manage existing ones
4. Enjoy your Minecraft server! 🎉

---

## 🌈 Server Types

Voxely supports various server types:

- 📜 **Paper** - High performance with plugin support
- 🎲 **Vanilla** - Pure Minecraft experience
- 🧶 **Fabric** - Lightweight mod support
- And more coming soon! ✨

---

## 🤝 Contributing

Feel free to contribute! Whether it's:

- 🐛 Reporting bugs
- 💡 Suggesting features
- 🔧 Submitting pull requests

All contributions are welcome!

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
