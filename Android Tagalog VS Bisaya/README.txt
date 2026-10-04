SNAKE GAME - PYTHON WINDOWS APP

1. Install Python 3.13 on Windows.
2. Open Window Terminal in this folder.
3. Install dependencies:
   py -3.13 -m pip install -r requirements.txt
4. Start the game (use 3.13 - pygame has no 3.14 wheel yet):
   py -3.13 main.py

TO CREATE A WINDOWS EXE:
Double-click build_windows.bat
The finished application will be:
   dist\SnakeGame.exe

FEATURES:
- Snake gameplay
- Arrow keys / WASD
- Score
- Increasing speed
- Player names
- 2-player local co-op/versus mode (Arrows vs WASD)
- Persistent top-10 leaderboard
- JSON score storage
- Main menu
- Game over screen
