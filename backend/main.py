import os
import sys

# Pastikan backend directory ada di sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, threaded=True)