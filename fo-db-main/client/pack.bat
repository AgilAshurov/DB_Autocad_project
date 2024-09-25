call venv\Scripts\activate
pyinstaller --onefile --windowed -i ..\app.ico main.py --name client --specpath spec --workpath build --distpath dist
pause
