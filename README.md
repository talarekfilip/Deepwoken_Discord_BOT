# Discord Gank Logger Bot 

A Discord bot designed for tracking and logging game ganks, featuring advanced statistics and management capabilities.

## 🌟 Features

- **Automatic Gank Logging** - Bot automatically detects and records gank information
- **Participant System** - Tracks participants for each gank
- **Statistics** - Advanced participation statistics
- **Admin Panel** - Manage logs and participants
- **Permission System** - Command access control
- **Database Integration** - MySQL data storage

## 🛠️ Requirements

- Python 3.8+
- Libraries:
  - discord.py
  - mysql-connector-python
  - pytz
- MySQL Server
- Discord Bot with appropriate permissions

## ⚙️ Installation

1. Clone the repository:
```bash
git clone https://github.com/Deepwoken_Discord_BOT
cd discord-gank-logger
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Configure `bot.py`:
   - Add your bot token
   - Configure channel IDs
   - Set up role permissions
   - Configure database connection

4. Run the bot:
```bash
python bot.py
```

## 📝 Commands

- `@ganklogs` - Displays gank history
- `@gankparty` - Shows participants from the last 5 ganks
- `@pavg` - Displays average participant attendance
- `@delete [id]` - Deletes a gank entry (admin only)

## 🔒 Configuration

Before running the bot, configure the following variables in `bot.py`:

```python
TOKEN = "YOUR_BOT_TOKEN"
SOURCE_CHANNEL_ID = 123456789
TARGET_CHANNEL_ID = 123456789
BOT_OWNER_ID = 123456789
BOT_STATUS_CHANNEL_ID = 123456789
ALLOWED_ROLES = [123456789, 987654321]
ALLOWED_CHANNELS = [123456789, 987654321]
```

## 📊 Database

The bot uses MySQL database to store:
- Gank logs
- Participants
- Statistics
- Timestamps

## 🤝 Contributing

Contributions are welcome! If you want to contribute to the project:
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## 📞 Contact

If you have questions or suggestions, contact us:
- Discord: talarek.filip

## 🙏 Acknowledgments

Thanks to everyone who contributed to this project! 
