import os
import sys
import webbrowser
from threading import Timer
from waitress import serve

# This is crucial for PyInstaller to find the Django project
# when running from the executable
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

from Budget_Tracker.wsgi import application

def open_browser():
    """
    Opens the default web browser to the application's URL.
    """
    webbrowser.open('http://127.0.0.1:8080')

def main():
    port = 8080
    
    # Open the browser automatically only when running the executable
    if getattr(sys, 'frozen', False):
        Timer(1.5, open_browser).start()

    print(f"Starting server at http://127.0.0.1:{port}")
    print("The application will be available in your web browser shortly.")
    print("Close this terminal window to stop the application.")
    
    serve(application, host='127.0.0.1', port=port)

if __name__ == "__main__":
    main()
