-- Migration: Host Group Configuration System with Georgian Geography
-- This migration adds support for dynamic host group monitoring and Georgian city/region mapping

-- Table 1: Monitored Host Groups
-- Stores which Zabbix host groups should be monitored
CREATE TABLE IF NOT EXISTS monitored_hostgroups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    groupid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    display_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: Georgian Regions
-- Master list of Georgian regions with coordinates for map visualization
CREATE TABLE IF NOT EXISTS georgian_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_en TEXT NOT NULL UNIQUE,
    name_ka TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 3: Georgian Cities
-- Cities mapped to regions with coordinates
CREATE TABLE IF NOT EXISTS georgian_cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_en TEXT NOT NULL UNIQUE,
    name_ka TEXT,
    region_id INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES georgian_regions(id)
);

-- Insert Georgian Regions with coordinates
INSERT OR IGNORE INTO georgian_regions (name_en, name_ka, latitude, longitude) VALUES
('Tbilisi', 'თბილისი', 41.7151, 44.8271),
('Adjara', 'აჭარა', 41.6168, 41.6367),
('Guria', 'გურია', 41.9517, 42.0403),
('Imereti', 'იმერეთი', 42.2708, 42.7089),
('Kakheti', 'კახეთი', 41.6488, 45.6970),
('Kvemo Kartli', 'ქვემო ქართლი', 41.5489, 44.7717),
('Mtskheta-Mtianeti', 'მცხეთა-მთიანეთი', 42.0669, 44.7211),
('Racha-Lechkhumi', 'რაჭა-ლეჩხუმი', 42.6708, 43.0403),
('Samegrelo-Zemo Svaneti', 'სამეგრელო-ზემო სვანეთი', 42.7389, 42.1708),
('Samtskhe-Javakheti', 'სამცხე-ჯავახეთი', 41.5489, 43.2717),
('Shida Kartli', 'შიდა ქართლი', 42.0756, 44.1028);

-- Insert Georgian Cities with coordinates (based on your Zabbix hosts)
INSERT OR IGNORE INTO georgian_cities (name_en, name_ka, region_id, latitude, longitude) VALUES
-- Adjara Region
('Batumi', 'ბათუმი', (SELECT id FROM georgian_regions WHERE name_en='Adjara'), 41.6168, 41.6367),
('Kobuleti', 'ქობულეთი', (SELECT id FROM georgian_regions WHERE name_en='Adjara'), 41.8167, 41.7833),
('Khelvachauri', 'ხელვაჩაური', (SELECT id FROM georgian_regions WHERE name_en='Adjara'), 41.5833, 41.6500),
('Khulo', 'ხულო', (SELECT id FROM georgian_regions WHERE name_en='Adjara'), 41.6500, 42.3000),
('Keda', 'ქედა', (SELECT id FROM georgian_regions WHERE name_en='Adjara'), 41.5667, 42.1000),

-- Guria Region
('Ozurgeti', 'ოზურგეთი', (SELECT id FROM georgian_regions WHERE name_en='Guria'), 41.9233, 42.0047),
('Lanchkhuti', 'ლანჩხუთი', (SELECT id FROM georgian_regions WHERE name_en='Guria'), 42.0833, 42.0833),
('Chokhatauri', 'ჩოხატაური', (SELECT id FROM georgian_regions WHERE name_en='Guria'), 41.9667, 42.1167),

-- Imereti Region
('Kutaisi', 'ქუთაისი', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.2500, 42.7000),
('Baghdati', 'ბაღდათი', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.0833, 42.8167),
('Vani', 'ვანი', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.0833, 42.5167),
('Zestaponi', 'ზესტაფონი', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.1167, 43.0500),
('Terjola', 'თერჯოლა', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.1667, 42.9833),
('Samtredia', 'სამტრედია', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.1500, 42.3333),
('Sachkhere', 'საჩხერე', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.3333, 43.4000),
('Tkibuli', 'ტყიბული', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.3333, 42.9833),
('Chiatura', 'ჭიათურა', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.2833, 43.3000),
('Tskaltubo', 'წყალტუბო', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.3333, 42.6000),
('Khoni', 'ხონი', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.3167, 42.4333),
('Kharagauli', 'ხარაგაული', (SELECT id FROM georgian_regions WHERE name_en='Imereti'), 42.0167, 43.1833),

-- Kakheti Region
('Telavi', 'თელავი', (SELECT id FROM georgian_regions WHERE name_en='Kakheti'), 41.9167, 45.4833),
('Gurjaani', 'გურჯაანი', (SELECT id FROM georgian_regions WHERE name_en='Kakheti'), 41.7333, 45.8000),
('Sagarejo', 'საგარეჯო', (SELECT id FROM georgian_regions WHERE name_en='Kakheti'), 41.7333, 45.3333),
('Dedoplistskaro', 'დედოფლისწყარო', (SELECT id FROM georgian_regions WHERE name_en='Kakheti'), 41.4500, 46.1167),
('Signagi', 'სიღნაღი', (SELECT id FROM georgian_regions WHERE name_en='Kakheti'), 41.6333, 45.9167),
('Lagodekhi', 'ლაგოდეხი', (SELECT id FROM georgian_regions WHERE name_en='Kakheti'), 41.8333, 46.2833),
('Kvareli', 'ყვარელი', (SELECT id FROM georgian_regions WHERE name_en='Kakheti'), 41.9500, 45.8167),
('Akhmeta', 'ახმეტა', (SELECT id FROM georgian_regions WHERE name_en='Kakheti'), 42.0333, 45.2167),

-- Kvemo Kartli Region
('Rustavi', 'რუსთავი', (SELECT id FROM georgian_regions WHERE name_en='Kvemo Kartli'), 41.5489, 44.9958),
('Bolnisi', 'ბოლნისი', (SELECT id FROM georgian_regions WHERE name_en='Kvemo Kartli'), 41.4500, 44.5333),
('Gardabani', 'გარდაბანი', (SELECT id FROM georgian_regions WHERE name_en='Kvemo Kartli'), 41.4667, 45.0833),
('Marneuli', 'მარნეული', (SELECT id FROM georgian_regions WHERE name_en='Kvemo Kartli'), 41.4667, 44.8000),
('Dmanisi', 'დმანისი', (SELECT id FROM georgian_regions WHERE name_en='Kvemo Kartli'), 41.3333, 44.3333),
('Tsalka', 'წალკა', (SELECT id FROM georgian_regions WHERE name_en='Kvemo Kartli'), 41.5833, 44.0833),
('Tetritskaro', 'თეთრიწყარო', (SELECT id FROM georgian_regions WHERE name_en='Kvemo Kartli'), 41.5833, 44.4667),

-- Mtskheta-Mtianeti Region
('Mtskheta', 'მცხეთა', (SELECT id FROM georgian_regions WHERE name_en='Mtskheta-Mtianeti'), 41.8464, 44.7211),
('Dusheti', 'დუშეთი', (SELECT id FROM georgian_regions WHERE name_en='Mtskheta-Mtianeti'), 42.0833, 44.7000),
('Tianeti', 'თიანეთი', (SELECT id FROM georgian_regions WHERE name_en='Mtskheta-Mtianeti'), 42.1167, 44.9667),
('Kazbegi', 'ყაზბეგი', (SELECT id FROM georgian_regions WHERE name_en='Mtskheta-Mtianeti'), 42.6667, 44.6333),

-- Racha-Lechkhumi Region
('Ambrolauri', 'ამბროლაური', (SELECT id FROM georgian_regions WHERE name_en='Racha-Lechkhumi'), 42.5167, 43.1500),
('Oni', 'ონი', (SELECT id FROM georgian_regions WHERE name_en='Racha-Lechkhumi'), 42.5833, 43.4500),
('Tsageri', 'ცაგერი', (SELECT id FROM georgian_regions WHERE name_en='Racha-Lechkhumi'), 42.6500, 42.7833),

-- Samegrelo-Zemo Svaneti Region
('Zugdidi', 'ზუგდიდი', (SELECT id FROM georgian_regions WHERE name_en='Samegrelo-Zemo Svaneti'), 42.5089, 41.8708),
('Poti', 'ფოთი', (SELECT id FROM georgian_regions WHERE name_en='Samegrelo-Zemo Svaneti'), 42.1500, 41.6667),
('Senaki', 'სენაკი', (SELECT id FROM georgian_regions WHERE name_en='Samegrelo-Zemo Svaneti'), 42.2667, 42.0667),
('Abasha', 'აბაშა', (SELECT id FROM georgian_regions WHERE name_en='Samegrelo-Zemo Svaneti'), 42.2000, 42.2000),
('Martvili', 'მარტვილი', (SELECT id FROM georgian_regions WHERE name_en='Samegrelo-Zemo Svaneti'), 42.4167, 42.3833),
('Mestia', 'მესტია', (SELECT id FROM georgian_regions WHERE name_en='Samegrelo-Zemo Svaneti'), 43.0500, 42.7333),
('Chkhorotsku', 'ჩხოროწყუ', (SELECT id FROM georgian_regions WHERE name_en='Samegrelo-Zemo Svaneti'), 42.5333, 42.0333),
('Khobi', 'ხობი', (SELECT id FROM georgian_regions WHERE name_en='Samegrelo-Zemo Svaneti'), 42.3167, 41.9000),

-- Samtskhe-Javakheti Region
('Akhaltsikhe', 'ახალციხე', (SELECT id FROM georgian_regions WHERE name_en='Samtskhe-Javakheti'), 41.6333, 42.9833),
('Borjomi', 'ბორჯომი', (SELECT id FROM georgian_regions WHERE name_en='Samtskhe-Javakheti'), 41.8333, 43.3833),
('Ninotsminda', 'ნინოწმინდა', (SELECT id FROM georgian_regions WHERE name_en='Samtskhe-Javakheti'), 41.2833, 43.6000),
('Akhalkalaki', 'ახალქალაქი', (SELECT id FROM georgian_regions WHERE name_en='Samtskhe-Javakheti'), 41.4000, 43.4833),
('Adigeni', 'ადიგენი', (SELECT id FROM georgian_regions WHERE name_en='Samtskhe-Javakheti'), 41.6833, 42.7000),
('Aspindza', 'ასპინძა', (SELECT id FROM georgian_regions WHERE name_en='Samtskhe-Javakheti'), 41.5667, 43.2500),
('Bakuriani', 'ბაკურიანი', (SELECT id FROM georgian_regions WHERE name_en='Samtskhe-Javakheti'), 41.7500, 43.5333),

-- Shida Kartli Region
('Gori', 'გორი', (SELECT id FROM georgian_regions WHERE name_en='Shida Kartli'), 41.9833, 44.1167),
('Kaspi', 'კასპი', (SELECT id FROM georgian_regions WHERE name_en='Shida Kartli'), 41.9167, 44.4167),
('Kareli', 'ქარელი', (SELECT id FROM georgian_regions WHERE name_en='Shida Kartli'), 42.0167, 44.0667),
('Khashuri', 'ხაშური', (SELECT id FROM georgian_regions WHERE name_en='Shida Kartli'), 41.9833, 43.6000),
('Java', 'ჯავა', (SELECT id FROM georgian_regions WHERE name_en='Shida Kartli'), 42.5667, 43.9833),

-- Tbilisi Districts/Areas
('Didube', 'დიდუბე', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7440, 44.7600),
('Saburtalo', 'საბურთალო', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7244, 44.7467),
('Vake', 'ვაკე', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.6977, 44.7614),
('Gldani', 'გლდანი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7838, 44.7353),
('Isani', 'ისანი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.6911, 44.8194),
('Samgori', 'სამგორი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7172, 44.8506),
('Chughureti', 'ჩუღურეთი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.6958, 44.8031),
('Nadzaladevi', 'ნაძალადევი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7256, 44.7661),
('Mtatsminda', 'მთაწმინდა', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.6903, 44.7961),
('Krtsanisi', 'კრწანისი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.6644, 44.8281),
('Varketili', 'ვარკეთილი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7244, 44.8642),
('Digomi', 'დიღომი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7647, 44.7328),
('Dighomi', 'დიღომი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7647, 44.7328),
('Lilo', 'ლილო', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.6944, 44.8931),
('Temka', 'თემქა', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7322, 44.8158),
('Vazisubani', 'ვაზისუბანი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7311, 44.8194),
('Marjanishvili', 'მარჯანიშვილი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7092, 44.7950),
('Aghmashenebeli', 'აღმაშენებელი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.7144, 44.8114),
('Mitskevichi', 'მიცკევიჩი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.6911, 44.8072),
('Avlabari', 'ავლაბარი', (SELECT id FROM georgian_regions WHERE name_en='Tbilisi'), 41.6922, 44.8139);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_cities_region ON georgian_cities(region_id);
CREATE INDEX IF NOT EXISTS idx_cities_name ON georgian_cities(name_en);
CREATE INDEX IF NOT EXISTS idx_monitored_active ON monitored_hostgroups(is_active);
