-- =========================
-- CREATE DATABASE
-- =========================
CREATE DATABASE IF NOT EXISTS building_carbon_db;
USE building_carbon_db;

-- =========================
-- 1. BUILDING TYPES
-- =========================
CREATE TABLE building_types (
    type_id INT PRIMARY KEY AUTO_INCREMENT,
    type_name VARCHAR(50) NOT NULL,
    scope1_intensity FLOAT NOT NULL COMMENT 'kg CO2/m2/day from gas/fuel',
    scope2_intensity FLOAT NOT NULL COMMENT 'kWh/m2/day electricity base',
    scope3_intensity FLOAT NOT NULL COMMENT 'kg CO2/m2/day embodied/commute estimate'
);

INSERT INTO building_types (type_name, scope1_intensity, scope2_intensity, scope3_intensity) VALUES
('Office',      0.05, 0.20, 0.03),
('Residential', 0.08, 0.10, 0.02),
('Commercial',  0.04, 0.25, 0.05),
('Industrial',  0.15, 0.30, 0.08),
('Hospital',    0.10, 0.40, 0.06),
('Educational', 0.03, 0.15, 0.02);

-- =========================
-- 2. CLIMATE ZONES
-- =========================
CREATE TABLE climate_zones (
    climate_id INT PRIMARY KEY AUTO_INCREMENT,
    zone_name VARCHAR(50) NOT NULL,
    summer_factor FLOAT NOT NULL,
    winter_factor FLOAT NOT NULL,
    monsoon_factor FLOAT NOT NULL
);

INSERT INTO climate_zones (zone_name, summer_factor, winter_factor, monsoon_factor) VALUES
('Hot & Dry',      1.4, 0.9, 1.1),
('Hot & Humid',    1.3, 1.0, 1.2),
('Cold',           0.9, 1.5, 1.0),
('Composite',      1.2, 1.1, 1.0),
('Moderate',       1.0, 1.0, 1.0),
('Warm & Humid',   1.2, 0.9, 1.2);

-- =========================
-- 3. REGIONS (with real Indian state grid emission factors)
-- =========================
CREATE TABLE regions (
    region_id INT PRIMARY KEY AUTO_INCREMENT,
    region_name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL DEFAULT 'India',
    grid_emission_factor FLOAT NOT NULL COMMENT 'kg CO2 per kWh',
    renewable_grid_pct FLOAT NOT NULL DEFAULT 0.0 COMMENT 'percent renewable in grid'
);

INSERT INTO regions (region_name, country, grid_emission_factor, renewable_grid_pct) VALUES
('Maharashtra',       'India', 0.82, 12.0),
('Delhi',             'India', 0.91, 8.0),
('Karnataka',         'India', 0.74, 28.0),
('Tamil Nadu',        'India', 0.78, 25.0),
('Gujarat',           'India', 0.85, 18.0),
('Rajasthan',         'India', 0.79, 32.0),
('West Bengal',       'India', 0.95, 5.0),
('Uttar Pradesh',     'India', 0.92, 7.0),
('Andhra Pradesh',    'India', 0.80, 20.0),
('Telangana',         'India', 0.83, 15.0),
('Madhya Pradesh',    'India', 0.88, 14.0),
('Kerala',            'India', 0.55, 45.0),
('Punjab',            'India', 0.86, 10.0),
('Haryana',           'India', 0.89, 9.0),
('Odisha',            'India', 0.90, 8.0),
('Other / National',  'India', 0.82, 15.0);

-- =========================
-- 4. MATERIALS (embodied carbon)
-- =========================
CREATE TABLE materials (
    material_id INT PRIMARY KEY AUTO_INCREMENT,
    material_name VARCHAR(100) NOT NULL,
    carbon_per_kg FLOAT NOT NULL COMMENT 'kg CO2 per kg of material',
    unit VARCHAR(20) NOT NULL DEFAULT 'kg'
);

INSERT INTO materials (material_name, carbon_per_kg, unit) VALUES
('Concrete (M25)',   0.13,  'kg'),
('Structural Steel', 1.77,  'kg'),
('Aluminium',        8.24,  'kg'),
('Glass',            0.91,  'kg'),
('Brick',            0.24,  'kg'),
('Timber',           0.42,  'kg'),
('Copper',           3.80,  'kg'),
('Plasterboard',     0.38,  'kg');

-- =========================
-- 5. BUILDINGS TABLE
-- =========================
CREATE TABLE buildings (
    building_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    floor_area FLOAT NOT NULL,
    workdays INT NOT NULL,
    occupancy_rate FLOAT NOT NULL DEFAULT 1.0 COMMENT '0.0 to 1.0',
    num_occupants INT NOT NULL DEFAULT 0,
    solar_offset_pct FLOAT NOT NULL DEFAULT 0.0 COMMENT 'percent energy from solar',
    type_id INT,
    climate_id INT,
    region_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (type_id) REFERENCES building_types(type_id),
    FOREIGN KEY (climate_id) REFERENCES climate_zones(climate_id),
    FOREIGN KEY (region_id) REFERENCES regions(region_id)
);

-- =========================
-- 6. BUILDING MATERIALS USED
-- =========================
CREATE TABLE building_material_usage (
    usage_id INT PRIMARY KEY AUTO_INCREMENT,
    building_id INT,
    material_id INT,
    quantity_kg FLOAT NOT NULL,
    embodied_emission FLOAT NOT NULL,
    FOREIGN KEY (building_id) REFERENCES buildings(building_id),
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
);

-- =========================
-- 7. BUILDING EMISSIONS (detailed breakdown)
-- =========================
CREATE TABLE building_emissions (
    emission_id INT PRIMARY KEY AUTO_INCREMENT,
    building_id INT,
    scope1_emission FLOAT NOT NULL DEFAULT 0,
    scope2_emission FLOAT NOT NULL DEFAULT 0,
    scope3_emission FLOAT NOT NULL DEFAULT 0,
    embodied_emission FLOAT NOT NULL DEFAULT 0,
    total_emission FLOAT NOT NULL,
    emission_per_m2 FLOAT NOT NULL,
    emission_rating VARCHAR(10) NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (building_id) REFERENCES buildings(building_id)
);



