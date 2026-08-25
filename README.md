# Smart Student Performance System

## Quickest way to run

```bash
bash setup.sh
```

This will create the venv, install everything, train the model and start the app.

---

If you run into any issues or need a fresh copy of the code:
```bash
git clone https://github.com/AhhadQamar/SmartStudentPerformanceSystem.git
```

---

## Manual setup

**1. Create a virtual environment**
```bash
python -m venv .venv
```

**2. Activate it**

Linux / Mac:
```bash
source .venv/bin/activate
```
Windows:
```bash
.venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

If that fails, install manually one by one:
```bash
pip install flask==3.1.1
pip install flask-sqlalchemy==3.1.1
pip install werkzeug==3.1.3
pip install scikit-learn==1.6.1
pip install pandas==2.2.3
```

**4. Train the model**
```bash
python scripts/train_model.py
```

**5. Start the app**
```bash
flask run
```

Open `http://127.0.0.1:5000` in your browser.
