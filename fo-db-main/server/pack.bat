call venv\Scripts\activate
pyinstaller --onefile main.py --name server --specpath spec --workpath build --distpath dist
pause
