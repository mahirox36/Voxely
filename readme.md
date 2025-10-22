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
  - Server logs viewer

- 🔧 **Advanced Features**

  - File manager for easy configuration
  - Plugin management system
  - Automated backups
  - Server settings customization
  - Players management
  - Config Editor
  - Multiple server types support (Paper, Vanilla, Fabric)

- 🎨 **Modern Web Interface**
  - Beautiful, responsive design
  - Real-time updates
  - Dark mode interface
  - Mobile-friendly

## 🛠️ Requirements

- 🖥️ **Operating System**: Windows, Linux, or MacOS
- ☕ **Java**: Java 17 or higher
- 🐍 **Python**: Python 3.12 or higher
- 🌐 **Node.js**: v18 or higher (for the web interface)

## 📦 Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/mahirox36/Voxely.git
   cd Voxely
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install frontend dependencies:

   ```bash
   cd frontend
   npm install
   ```

4. Start the application:

   ```bash
   # In the backend directory
   python -m uvicorn core:app --port 25401
   # In the frontend directory
   npm run build
   npm run start
   ```

## 🎮 Usage

1. Access the web interface at `http://localhost:3000`
2. Log in with your credentials
3. Create a new server or manage existing ones
4. Enjoy your Minecraft server! 🎉

## 🌈 Server Types

Voxely supports various server types:

- 📜 **Paper** - High performance with plugin support
- 🎲 **Vanilla** - Pure Minecraft experience
- 🧶 **Fabric** - Lightweight mod support
- And more coming soon! ✨

## 🤝 Contributing

Feel free to contribute! Whether it's:

- 🐛 Reporting bugs
- 💡 Suggesting features
- 🔧 Submitting pull requests

All contributions are welcome!

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 💖 Support

Found this helpful? Give us a star! ⭐

---

Made with 💝 for the Minecraft community
