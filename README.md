# GuardianAI : An Intelligent Real-Time Digital Safety Platform

**GuardianAI** is a **startup-grade, real-time AI platform** designed for parents, schools, and enterprises to monitor online activity and protect users from harmful content. It combines **LLM-powered contextual reasoning, prompt-engineered moderation, age-aware evaluation, and explainable alerts** across multiple languages.  

---

## Key Features

* **Parental Authentication System**  
  Register, log in, and securely manage multiple children under one account.

* **Multi-Child Management**  
  Parents can monitor multiple children, each with separate activity logs.

* **Real-Time Browsing Activity Logging**  
  Chrome extension captures page titles, URLs, timestamps, and risk assessments.

* **Hybrid Risk Detection Engine**  
  - Layer 1: Fast keyword and lightweight ML filtering  
  - Layer 2: LLM-based contextual reasoning for risk categorization  
  - Layer 3: Age-aware evaluation to ensure developmental appropriateness  
  - Outputs structured JSON: category, risk level, confidence score

* **Explainability Agent**  
  - Generates **human-readable explanations** for flagged content  
  - Example: *“This page was blocked because it contains implicit sexual references unsafe for minors.”*

* **Multi-Language Support**  
  - Detects content in English, Hindi, Telugu, Hinglish, and more  
  - Translates and analyzes for consistent risk scoring

* **Modern Admin Dashboard**  
  - Live alerts, risk trends, category & language analytics  
  - Displays explanations for flagged content  
  - Built with React, Chart.js, and Django backend

* **Privacy and Compliance**  
  - Anonymized browsing logs  
  - Encrypted storage in MongoDB  
  - Consent warnings for parents

---


## 📁 Project Structure

```
safeweb/
├── chrome_extension/        ← Chrome extension files
├── data/                    ← (For static data files if required)
├── monitor/                 ← Django app (core logic and views)
│   ├── migrations/
│   ├── static/
│   ├── templates/
│   ├── utils/
│   │   ├── risk_engine.py ← Hybrid + age-aware risk scoring
│   │   ├── explainability_agent.py← LLM explanations
│   │   ├── alert_engine.py
│   │   ├── data_preprocessor.py
│   │   ├── nsfw_detector.py
│   │   ├── predict_behaviour.py
│   │   └── query_analyzer.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── mongo_config.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── safeweb/                 ← Django project configuration
├── manage.py
```


### 2️⃣ Setup Python Environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3️⃣ MongoDB Setup

* Install and start MongoDB locally or use a cloud service.
* Update your MongoDB URI in:

  `monitor/mongo_config.py`

Example:

```python
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "safewebguard_db"
```

### 4️⃣ Django Setup

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 5️⃣ Chrome Extension Setup

* Open `chrome://extensions/`
* Enable **Developer Mode**
* Click **Load Unpacked**
* Select the `chrome_extension/` folder
* Set child email through the extension popup

---

## 🔄 System Flow Diagram

```
Child Browsing → Chrome Extension → Content Ingestion Layer → Risk Engine (Keyword + ML + LLM)
→ Explainability Agent → MongoDB Storage → Admin Dashboard → Real-Time Alerts / Analytics

```

---

## 🖥️ Usage Guide

* Visit: `http://127.0.0.1:8000/`
* Register as a parent.
* Add child emails.
* Install Chrome Extension on your child's device.
* Monitor browsing logs in real-time through the dashboard.

---

## 🔒 Important Notes

* All predictions rely on external APIs integrated in `monitor/utils/`.
* Ensure backend URL in the Chrome extension matches your Django server URL.
* Works with MongoDB only; no SQL databases configured.

---

## 📄 Screenshots
<img width="1919" height="986" alt="Register-page" src="https://github.com/user-attachments/assets/ead3e015-4657-4752-a209-59a599ce9c6c" />
<img width="1831" height="964" alt="Login - Page" src="https://github.com/user-attachments/assets/e6fd1ad4-4ae0-4dcb-a2d1-3328ecab4984" />
<img width="1795" height="919" alt="select - child" src="https://github.com/user-attachments/assets/f7f8a3e8-5139-4efc-876a-efd1132e451a" />
<img width="616" height="474" alt="Chrome Extension" src="https://github.com/user-attachments/assets/a2c1c9ea-a06e-427e-b637-806e0339a8f6" />
<img width="1884" height="972" alt="dashboard of user" src="https://github.com/user-attachments/assets/b9550e30-0a66-4392-add1-30a8936cea76" />
<img width="1833" height="874" alt="Dashboard of New User" src="https://github.com/user-attachments/assets/cbf69b17-6a96-49c9-92af-cbc2571b3d4c" />
<img width="1479" height="726" alt="Parent Alert Through Gmail" src="https://github.com/user-attachments/assets/b022787a-2e69-4e59-b45e-62ec072607ba" />



---

## ✍️ Developed By

* **Nagulapally Bhargavi** - https://github.com/bhargavi852004

