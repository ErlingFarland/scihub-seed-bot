if [ ! -d venv ]; then
  python -m venv venv
  source venv
  pip install -r requirements.txt
else
  source venv
fi

python main.py
