from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling, Error as MySQLError
import os
import logging
from dotenv import load_dotenv
load_dotenv() 

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ── DB credentials — edit here OR set environment variables ───────────────────
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_USER     = os.getenv("DB_USER",     "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")      # ← change if needed
DB_NAME     = os.getenv("DB_NAME",     "building_carbon_db")

# ── Lazy pool — built on first request, NOT at import time ────────────────────
#    This prevents a startup crash when MySQL isn't ready yet,
#    and makes the real error visible via /test-db instead of a silent hang.
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        logger.info("Creating connection pool → %s@%s/%s", DB_USER, DB_HOST, DB_NAME)
        _pool = pooling.MySQLConnectionPool(
            pool_name="carbon_pool",
            pool_size=5,
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        logger.info("Pool created OK.")
    return _pool

def get_conn():
    return get_pool().get_connection()


# ── Helpers ────────────────────────────────────────────────────────────────────
def co2_equivalents(kg_co2):
    return {
        "flights_mumbai_delhi": round(kg_co2 / 194,    1),
        "car_km":               round(kg_co2 / 0.21,   0),
        "trees_year":           round(kg_co2 / 21,     1),
        "led_bulb_hours":       round(kg_co2 / 0.008,  0),
        "smartphones_charged":  round(kg_co2 / 0.0085, 0),
    }

def seasonal_avg_factor(summer, winter, monsoon, workdays):
    """Weighted average of seasonal climate factors for Indian year."""
    s = round(workdays * 4 / 12)
    m = round(workdays * 3 / 12)
    w = workdays - s - m
    return round((summer * s + monsoon * m + winter * w) / workdays, 4)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def home():
    return render_template('index.html')


# ── Debug route — open http://127.0.0.1:5000/test-db in browser ───────────────
@app.route('/test-db')
def test_db():
    """
    Use this to diagnose connection problems.
    It will tell you exactly what errno MySQL returned.
    """
    try:
        conn = get_conn()
        cur  = conn.cursor()
        results = {}
        for table in ('building_types', 'climate_zones', 'regions', 'materials'):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            results[table] = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify({"status": "OK - connected", "row_counts": results,
                        "host": DB_HOST, "database": DB_NAME})
    except MySQLError as e:
        hints = {
            1045: "Wrong username or password.",
            2003: "MySQL is not running, or wrong host/port.",
            1049: "Database does not exist — import building_carbon_db.sql first.",
        }
        return jsonify({
            "status":   "FAILED",
            "errno":    e.errno,
            "error":    str(e),
            "hint":     hints.get(e.errno, "Check MySQL logs."),
            "config":   {"host": DB_HOST, "user": DB_USER, "database": DB_NAME},
        }), 500
    except Exception as e:
        return jsonify({"status": "FAILED", "error": str(e)}), 500


# ── /meta — all dropdown data ─────────────────────────────────────────────────
@app.route('/meta')
def get_meta():
    try:
        conn = get_conn()
        cur  = conn.cursor(dictionary=True)

        cur.execute("SELECT type_id, type_name FROM building_types ORDER BY type_id")
        building_types = cur.fetchall()

        cur.execute("SELECT climate_id, zone_name FROM climate_zones ORDER BY climate_id")
        climates = cur.fetchall()

        cur.execute("""SELECT region_id, region_name, grid_emission_factor, renewable_grid_pct
                       FROM regions ORDER BY region_name""")
        regions = cur.fetchall()

        cur.execute("SELECT material_id, material_name, carbon_per_kg FROM materials ORDER BY material_name")
        materials = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({
            "building_types": building_types,
            "climates":       climates,
            "regions":        regions,
            "materials":      materials,
        })

    except MySQLError as e:
        logger.error("/meta MySQLError %s: %s", e.errno, e)
        return jsonify({"error": str(e), "errno": e.errno}), 500
    except Exception as e:
        logger.exception("/meta error")
        return jsonify({"error": str(e)}), 500


# ── /calculate ────────────────────────────────────────────────────────────────
@app.route('/calculate', methods=['POST'])
def calculate():
    conn = cur = None
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # ── Validate required fields ──────────────────────────────────────────
        for field in ('name', 'floor_area', 'workdays', 'type_id', 'climate_id', 'region_id'):
            if not data.get(field) and data.get(field) != 0:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        name           = str(data['name']).strip()[:100]
        floor_area     = float(data['floor_area'])
        workdays       = int(data['workdays'])
        occupancy_rate = max(0.1, min(1.0, float(data.get('occupancy_rate') or 1.0)))
        num_occupants  = max(0,   int(data.get('num_occupants') or 0))
        solar_offset   = max(0.0, min(1.0, float(data.get('solar_offset_pct') or 0) / 100))
        type_id        = int(data['type_id'])
        climate_id     = int(data['climate_id'])
        region_id      = int(data['region_id'])
        materials_used = data.get('materials') or []

        if floor_area <= 0 or workdays <= 0:
            return jsonify({"error": "Floor area and workdays must be positive"}), 400

        conn = get_conn()
        cur  = conn.cursor(dictionary=True)

        # Building type
        cur.execute("SELECT * FROM building_types WHERE type_id = %s", (type_id,))
        btype = cur.fetchone()
        if not btype:
            return jsonify({"error": f"No building type with id {type_id}"}), 400

        # Climate zone
        cur.execute("SELECT * FROM climate_zones WHERE climate_id = %s", (climate_id,))
        climate = cur.fetchone()
        if not climate:
            return jsonify({"error": f"No climate zone with id {climate_id}"}), 400

        climate_factor = seasonal_avg_factor(
            climate['summer_factor'], climate['winter_factor'],
            climate['monsoon_factor'], workdays
        )

        # Region
        cur.execute("SELECT * FROM regions WHERE region_id = %s", (region_id,))
        region = cur.fetchone()
        if not region:
            return jsonify({"error": f"No region with id {region_id}"}), 400

        effective_grid = (
            region['grid_emission_factor']
            * (1 - region['renewable_grid_pct'] / 100.0 * 0.5)
        )

        # ── Scope 1: Direct (fuel / gas boilers) ─────────────────────────────
        scope1_emission = (
            btype['scope1_intensity'] * floor_area
            * workdays * climate_factor * occupancy_rate
        )

        # ── Scope 2: Grid electricity ─────────────────────────────────────────
        energy_kwh      = (
            btype['scope2_intensity'] * floor_area
            * workdays * climate_factor * occupancy_rate
        )
        scope2_emission  = energy_kwh * (1 - solar_offset) * effective_grid

        # ── Scope 3: Supply chain + commuting ────────────────────────────────
        scope3_base     = btype['scope3_intensity'] * floor_area * workdays * occupancy_rate
        commute         = num_occupants * 2.5 * workdays if num_occupants > 0 else 0
        scope3_emission = scope3_base + commute

        # ── Embodied carbon from materials ────────────────────────────────────
        embodied_emission  = 0.0
        material_breakdown = []
        for m in materials_used:
            mid = int(m.get('material_id') or 0)
            qty = float(m.get('quantity_kg') or 0)
            if mid > 0 and qty > 0:
                cur.execute(
                    "SELECT material_id, material_name, carbon_per_kg FROM materials WHERE material_id = %s",
                    (mid,)
                )
                mat = cur.fetchone()
                if mat:
                    em = qty * mat['carbon_per_kg']
                    embodied_emission += em
                    material_breakdown.append({
                        "name": mat['material_name'], "qty_kg": qty,
                        "emission_kg": round(em, 2),
                    })

        total_emission  = scope1_emission + scope2_emission + scope3_emission + embodied_emission
        emission_per_m2 = total_emission / floor_area

        # ── Rating ────────────────────────────────────────────────────────────
        if   emission_per_m2 < 50:  level, stars = "Excellent", 5
        elif emission_per_m2 < 100: level, stars = "Good",      4
        elif emission_per_m2 < 200: level, stars = "Average",   3
        elif emission_per_m2 < 350: level, stars = "Poor",      2
        else:                       level, stars = "Critical",  1

        # ── Persist ───────────────────────────────────────────────────────────
        cur.execute("""
            INSERT INTO buildings
                (name, floor_area, workdays, occupancy_rate,
                 num_occupants, solar_offset_pct, type_id, climate_id, region_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (name, floor_area, workdays, occupancy_rate,
              num_occupants, round(solar_offset * 100, 2), type_id, climate_id, region_id))
        conn.commit()
        building_id = cur.lastrowid

        cur.execute("""
            INSERT INTO building_emissions
                (building_id, scope1_emission, scope2_emission, scope3_emission,
                 embodied_emission, total_emission, emission_per_m2, emission_rating)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (building_id,
              round(scope1_emission,  2), round(scope2_emission,  2),
              round(scope3_emission,  2), round(embodied_emission, 2),
              round(total_emission,   2), round(emission_per_m2,   2), level))

        for m in material_breakdown:
            cur.execute("""
                INSERT INTO building_material_usage
                    (building_id, material_id, quantity_kg, embodied_emission)
                SELECT %s, material_id, %s, %s FROM materials WHERE material_name = %s
            """, (building_id, m['qty_kg'], m['emission_kg'], m['name']))

        conn.commit()

        return jsonify({
            "building_id":     building_id,
            "total_emission":  round(total_emission,  2),
            "emission_per_m2": round(emission_per_m2, 2),
            "level":  level,
            "stars":  stars,
            "breakdown": {
                "scope1":   round(scope1_emission,  2),
                "scope2":   round(scope2_emission,  2),
                "scope3":   round(scope3_emission,  2),
                "embodied": round(embodied_emission, 2),
            },
            "details": {
                "energy_kwh":      round(energy_kwh,      0),
                "climate_factor":  climate_factor,
                "grid_factor":     round(effective_grid,   4),
                "solar_offset_pct": round(solar_offset * 100, 1),
                "region":          region['region_name'],
            },
            "equivalents": co2_equivalents(total_emission),
            "materials":   material_breakdown,
        })

    except MySQLError as e:
        logger.error("/calculate MySQLError %s: %s", e.errno, e)
        if conn: conn.rollback()
        return jsonify({"error": f"Database error (errno {e.errno}): {e}"}), 500
    except ValueError as e:
        return jsonify({"error": f"Invalid value: {e}"}), 400
    except Exception as e:
        logger.exception("/calculate unexpected error")
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:  cur.close()
        if conn: conn.close()


# ── /history ──────────────────────────────────────────────────────────────────
@app.route('/history')
def history():
    try:
        conn = get_conn()
        cur  = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT b.name, b.floor_area, bt.type_name, r.region_name,
                   e.total_emission, e.emission_per_m2, e.emission_rating, e.calculated_at
            FROM   buildings b
            JOIN   building_emissions e  ON b.building_id = e.building_id
            JOIN   building_types     bt ON b.type_id     = bt.type_id
            JOIN   regions            r  ON b.region_id   = r.region_id
            ORDER  BY e.calculated_at DESC
            LIMIT  10
        """)
        rows = cur.fetchall()
        for row in rows:
            row['calculated_at'] = str(row['calculated_at'])
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        logger.error("/history error: %s", e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)