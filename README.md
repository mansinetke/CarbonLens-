# CarbonLens-
India-specific building carbon calculator using GHG Protocol
# 🌍 CarbonLens — Building Carbon Emissions Calculator (India)

## 📌 Overview

CarbonLens is a full-stack web application that estimates carbon emissions of buildings in India using the **GHG Protocol (Scope 1, 2, 3 + Embodied Carbon)**.

It integrates **India-specific parameters** such as:

* State-level electricity emission factors
* Climate zones (ECBC)
* Seasonal HVAC adjustments
* Construction material emissions

---

## 🚀 Features

* ✅ Scope 1, Scope 2, Scope 3 emission calculation
* ✅ Embodied carbon from materials
* ✅ India-specific grid emission factors
* ✅ Climate-based seasonal weighting
* ✅ Solar/renewable offset support
* ✅ CO₂ equivalency (cars, flights, trees, etc.)
* ✅ Emission rating system (Excellent → Critical)
* ✅ History of last 10 calculations

---

## 🏗️ Tech Stack

**Frontend**

* HTML5, CSS3, JavaScript

**Backend**

* Python (Flask)

**Database**

* MySQL

---

## 📊 System Architecture

* Presentation Layer → HTML/CSS/JS
* Application Layer → Flask API
* Data Layer → MySQL

---

## 🗂️ Database Design

* building_types
* climate_zones
* regions
* materials
* buildings
* building_emissions
* building_material_usage

---

## 🖼️ Screenshots

### 🏠 Home Page

![Home](screenshots/Home.png)

### 📝 Input Form

![Input](screenshots/Input_1.png)
![Input](screenshots/Input_2.png)


### 📊 Result Output

![Result](screenshots/Result_1.png)
![Result](screenshots/Result_2.png)


### 🗄️ Database Schema

![Database](screenshots/db_tables_overview.png)
![Database](screenshots/db_buildings_data.png)
![Database](screenshots/db_buildings_structure.png)


### 📜 History Panel

![History](screenshots/db_history_query.png)
---

## ⚙️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/CarbonLens.git
cd CarbonLens
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Setup MySQL Database

```sql
SOURCE building_carbon_db.sql;
```

---

### 4️⃣ Configure Database (optional)

In `app.py`:

```python
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "your_password"
DB_NAME = "building_carbon_db"
```

---

### 5️⃣ Run Application

```bash
python app.py
```

Open:

```
http://127.0.0.1:5000
```

---

## 📡 API Endpoints

| Endpoint   | Method | Description         |
| ---------- | ------ | ------------------- |
| /          | GET    | Frontend            |
| /meta      | GET    | Dropdown data       |
| /calculate | POST   | Calculate emissions |
| /history   | GET    | Recent calculations |
| /test-db   | GET    | DB connection test  |

---

## 📈 Sample Output

* Total Emission: 133,895 kg CO₂/year
* Emission Intensity: 26.78 kg CO₂/m²/year
* Rating: ⭐⭐⭐⭐⭐ Excellent

---

## 🎯 Future Scope

* AI-based emission prediction
* Real-time IoT integration
* Mobile app version
* Cloud deployment

---

## 👩‍💻 Author

**Mansi Netke**


---

## 📜 License

This project is for academic and educational purposes.
