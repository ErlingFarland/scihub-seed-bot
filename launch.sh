if [ -d venv ]; then
  source venv
else
  python -m venv venv
  source venv
  pip install -r requirements.txt
fi

python main.py
