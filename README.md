# Smart Student Performance System

If you run into any issues or need a fresh copy of the code:

```bash
git clone https://github.com/AhhadQamar/SmartStudentPerformanceSystem.git
```

---

## How to run

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

**4. Train the model**
```bash
python scripts/train_model.py
```

**5. Start the app**
```bash
flask run
```

Open `http://127.0.0.1:5000` in your browser.
