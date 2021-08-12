# ChessBot
Code for a Python Discord API-based chatbot allowing members of a Discord server to play chess against one or more opponents, including the Stockfish Engine, in multiple game formats.

The bot will reply to the user in whichever channel the user sends a message, so bot permissions must be set accordingly by the server owner.

Once running, query the bot by beginning messages with the vertical line character, "|", eg:
> |help

Example board image, which would be sent to the user through the discord server:

![output](https://user-images.githubusercontent.com/66851249/129278495-f33c1997-6aa6-4d15-b1e4-6a5ed7b14dc1.png)

Requires the following:
- [Python Chess](https://python-chess.readthedocs.io/en/latest/)
- [discord.py](https://discordpy.readthedocs.io/en/stable/api.html)
- [svglib](https://pypi.org/project/svglib/)
- [reportlab](https://pypi.org/project/reportlab/)
- [stockfish.exe](https://stockfishchess.org/)

