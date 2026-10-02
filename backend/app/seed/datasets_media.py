"""Demo datasets (with synthetic records) and media records.

All dataset values are SYNTHETIC — generated with seasonal cycles plus noise purely to demonstrate
the dataset explorer. They are not observations and must not be used for scientific conclusions.
"""
from datetime import date, datetime, timedelta

import numpy as np

SYNTH_LICENSE = "Synthetic demonstration data (CC0)"
SYNTH_SOURCE = "PolarNexus demo generator (synthetic values)"


def _season(day_of_year: np.ndarray, peak_doy: int) -> np.ndarray:
    return np.cos(2 * np.pi * (day_of_year - peak_doy) / 365.25)


def _dates(start: date, end: date, step_days: int) -> list[datetime]:
    out, d = [], datetime(start.year, start.month, start.day)
    while d.date() <= end:
        out.append(d)
        d += timedelta(days=step_days)
    return out


def gen_sea_ice(rng):
    ts = _dates(date(2019, 1, 1), date(2024, 12, 31), 7)
    doy = np.array([t.timetuple().tm_yday for t in ts])
    s = _season(doy, 258)  # max around mid-September
    yearly = {y: rng.normal(0, 4) for y in range(2019, 2025)}
    out = []
    for t, sv in zip(ts, s):
        conc = np.clip(62 + 33 * sv + yearly[t.year] + rng.normal(0, 4), 0, 100)
        lat = -66.0 - 2.4 * (1 - sv) + rng.normal(0, 0.25)  # ice-edge sample latitude
        out.append((t, round(float(lat), 3), round(float(76.4 + rng.normal(0, 0.6)), 3), {
            "sea_ice_concentration": round(float(conc), 1),
            "surface_temperature": round(float(-9 - 10 * sv + rng.normal(0, 2.2)), 1),
        }))
    return out


def gen_weather(rng, base_t, amp_t, lat, lon, start=date(2023, 1, 1), end=date(2024, 12, 31)):
    ts = _dates(start, end, 3)
    out = []
    for t in ts:
        sv = _season(np.array([t.timetuple().tm_yday]), 200)[0]  # coldest ~July
        out.append((t, lat, lon, {
            "temperature": round(float(base_t - amp_t * sv + rng.normal(0, 3)), 1),
            "pressure": round(float(985 + rng.normal(0, 7)), 1),
            "wind_speed": round(float(max(0, 8 + 4 * sv + rng.gamma(2, 2))), 1),
            "humidity": round(float(np.clip(62 + rng.normal(0, 10), 15, 100)), 0),
        }))
    return out


def gen_atmos(rng):
    ts = _dates(date(2023, 1, 1), date(2024, 12, 31), 3)
    out = []
    for t in ts:
        doy = t.timetuple().tm_yday
        haze = np.exp(-((doy - 95) ** 2) / (2 * 35 ** 2))  # spring haze bump
        out.append((t, 78.92, 11.93, {
            "location": "Ny-Ålesund",
            "temperature": round(float(-4 - 9 * _season(np.array([doy]), 40)[0] + rng.normal(0, 2.5)), 1),
            "pressure": round(float(1008 + rng.normal(0, 8)), 1),
            "humidity": round(float(np.clip(75 + rng.normal(0, 9), 30, 100)), 0),
            "aerosol_concentration": round(float(max(20, 160 + 420 * haze + rng.normal(0, 60))), 0),
            "black_carbon": round(float(max(2, 12 + 55 * haze + rng.normal(0, 8))), 1),
        }))
    return out


def gen_ozone(rng):
    ts = _dates(date(2021, 1, 1), date(2024, 12, 31), 5)
    out = []
    for t in ts:
        doy = t.timetuple().tm_yday
        if 140 < doy < 225:  # polar night — no sun-based measurements
            continue
        hole = np.exp(-((doy - 275) ** 2) / (2 * 22 ** 2))
        out.append((t, -70.77, 11.73, {"total_ozone": round(float(300 - 150 * hole + rng.normal(0, 12)), 0)}))
    return out


def gen_ctd(rng):
    out = []
    stations = [(-45 - i * 2.2, 57.5 + i * 1.2) for i in range(10)]
    base = datetime(2024, 1, 20)
    for si, (lat, lon) in enumerate(stations):
        surf_t = 12 - si * 1.35
        for depth in [5, 25, 50, 75, 100, 150, 200, 300, 400, 600, 800, 1000]:
            ww = -1.5 if si >= 6 and 50 <= depth <= 150 else None
            temp = surf_t * np.exp(-depth / 450) + (ww if ww else 0) * 0.8 + (1.6 if si >= 6 and depth >= 300 else 0)
            out.append((base + timedelta(days=si), round(lat, 2), round(lon, 2), {
                "station": f"CTD-{si + 1:02d}", "depth": depth,
                "temperature": round(float(temp + rng.normal(0, 0.1)), 2),
                "salinity": round(float(33.8 + 0.0012 * depth + rng.normal(0, 0.03)), 3),
            }))
    return out


def gen_simple_series(rng, start, end, step, var, base, amp, peak, noise, lat, lon, floor=None, extra=None):
    out = []
    for t in _dates(start, end, step):
        v = base + amp * _season(np.array([t.timetuple().tm_yday]), peak)[0] + rng.normal(0, noise)
        if floor is not None:
            v = max(floor, v)
        vals = {var: round(float(v), 2)}
        if extra:
            vals.update(extra(t, rng))
        out.append((t, lat, lon, vals))
    return out


def gen_mass_balance(rng):
    out = []
    for glacier in ["Glacier A (benchmark)", "Glacier B", "Glacier C (debris-covered)"]:
        for y in range(2015, 2024):
            mb = -0.55 + rng.normal(0, 0.35) + (0.25 if "debris" in glacier else 0)
            out.append((datetime(y, 9, 30), 32.4, 77.6, {"glacier": glacier, "mass_balance": round(float(mb), 2)}))
    return out


def gen_ice_core(rng):
    out, val = [], -24.0
    for y in range(1800, 2021, 2):
        val = 0.85 * val + 0.15 * (-24.0 + (0.4 if y > 1960 else 0)) + rng.normal(0, 0.45)
        acc = 0.32 + (0.04 if y > 1960 else 0) + rng.normal(0, 0.05)
        out.append((datetime(y, 1, 1), -70.5, 11.9, {"year": y, "delta_18O": round(float(val), 2),
                                                     "accumulation": round(float(acc), 3)}))
    return out


def gen_microbiology(rng):
    out = []
    lakes = ["Lake L1", "Lake L2", "Lake L3", "Lake L4", "Lake L5", "Lake L6"]
    for i, lake in enumerate(lakes):
        for rep in range(1, 5):
            cond = 40 + i * 35 + rng.normal(0, 8)
            out.append((datetime(2022, 1, 10 + i), -70.75 + rng.normal(0, 0.01), 11.6 + i * 0.03, {
                "lake": lake, "sample": f"{lake}-R{rep}",
                "conductivity": round(float(cond), 1),
                "nitrate": round(float(max(0.01, 0.05 + 0.01 * i + rng.normal(0, 0.02))), 3),
                "cyanobacteria_relative_abundance": round(float(np.clip(55 - i * 4 + rng.normal(0, 6), 5, 95)), 1),
                "shannon_diversity": round(float(2.2 + 0.1 * i + rng.normal(0, 0.15)), 2),
            }))
    return out


def gen_glacier_velocity(rng):
    out = []
    for g, base in [("Outlet glacier 1", 145), ("Outlet glacier 2", 90)]:
        for t in _dates(date(2018, 1, 1), date(2024, 12, 1), 30):
            out.append((t, -70.3, 12.5, {"glacier": g, "surface_velocity": round(float(base + rng.normal(0, 6)), 1)}))
    return out


def gen_arctic_extent(rng):
    out = []
    for y in range(1990, 2025):
        anomaly = -0.07 * (y - 1990) + rng.normal(0, 0.35)
        out.append((datetime(y, 9, 15), 80.0, 0.0, {"year": y, "september_extent_anomaly_index": round(float(anomaly), 2)}))
    return out


def gen_geomag(rng):
    out = []
    for t in _dates(date(2022, 1, 1), date(2022, 12, 31), 2):
        storm = rng.random() < 0.06
        out.append((t, -69.41, 76.19, {
            "h_component_variation": round(float(rng.normal(0, 25) + (rng.normal(-180, 60) if storm else 0)), 1),
            "kp_index": int(np.clip(round(rng.gamma(2, 1.0) + (4 if storm else 0)), 0, 9)),
        }))
    return out


DATASETS = [
    dict(slug="antarctic-sea-ice-observations", title="Antarctic Sea Ice Observations", region="Antarctic",
         data_type="Time series", start=date(2019, 1, 1), end=date(2024, 12, 31),
         spatial="Prydz Bay sector, Indian Ocean sector of the Southern Ocean",
         description=("Weekly sea-ice concentration and surface temperature at sampled ice-edge positions in the Prydz "
                      "Bay sector, supporting the Antarctic Sea Ice Variability Study. Synthetic demonstration values."),
         variables=[("date", "ISO date", "Observation date"), ("latitude", "°N", "Ice-edge sample latitude"),
                    ("longitude", "°E", "Sample longitude"), ("sea_ice_concentration", "%", "Fraction of area covered by ice"),
                    ("surface_temperature", "°C", "Near-surface air temperature")],
         fmt="CSV", year=2024, gen=gen_sea_ice, topics=["sea-ice", "remote-sensing"], stations=["bharati", "prydz-bay-site"],
         expeditions=["isea-43"], keywords=["sea ice", "concentration", "Prydz Bay"]),
    dict(slug="polar-atmospheric-observations", title="Polar Atmospheric Observations", region="Arctic",
         data_type="Time series", start=date(2023, 1, 1), end=date(2024, 12, 31), spatial="Ny-Ålesund, Svalbard",
         description="Temperature, pressure, humidity, aerosol number concentration and black carbon at Ny-Ålesund. Synthetic demonstration values.",
         variables=[("timestamp", "ISO datetime", "Observation time"), ("location", "text", "Site name"),
                    ("temperature", "°C", "Air temperature"), ("pressure", "hPa", "Surface pressure"),
                    ("humidity", "%", "Relative humidity"), ("aerosol_concentration", "particles/cm³", "Aerosol number concentration"),
                    ("black_carbon", "ng/m³", "Black carbon mass concentration")],
         fmt="CSV", year=2024, gen=gen_atmos, topics=["aerosols", "polar-atmosphere"], stations=["himadri"],
         expeditions=["arctic-2023"], keywords=["aerosol", "Arctic haze", "black carbon"]),
    dict(slug="southern-ocean-ctd-profiles", title="Southern Ocean CTD Profiles", region="Southern Ocean",
         data_type="Profiles", start=date(2024, 1, 20), end=date(2024, 1, 30), spatial="45°S–65°S transect, Indian Ocean sector",
         description="Temperature and salinity profiles from a meridional CTD transect across Southern Ocean fronts. Synthetic demonstration values.",
         variables=[("station", "id", "CTD station"), ("depth", "m", "Depth"), ("temperature", "°C", "Sea temperature"),
                    ("salinity", "PSU", "Practical salinity")],
         fmt="NetCDF / CSV", year=2024, gen=gen_ctd, topics=["physical-oceanography", "southern-ocean"],
         stations=["prydz-bay-site"], expeditions=["soe-2024", "isea-43"], keywords=["CTD", "fronts", "Winter Water"]),
    dict(slug="maitri-surface-weather", title="Maitri Surface Weather Observations", region="Antarctic",
         data_type="Time series", start=date(2023, 1, 1), end=date(2024, 12, 31), spatial="Maitri, Schirmacher Oasis",
         description="Three-day surface weather summaries from Maitri: temperature, pressure, wind speed and humidity. Synthetic demonstration values.",
         variables=[("temperature", "°C", "Air temperature"), ("pressure", "hPa", "Station pressure"),
                    ("wind_speed", "m/s", "Mean wind speed"), ("humidity", "%", "Relative humidity")],
         fmt="CSV", year=2024, gen=lambda r: gen_weather(r, -10, 9, -70.77, 11.73), topics=["polar-meteorology"],
         stations=["maitri"], expeditions=["isea-40"], keywords=["weather", "katabatic", "blizzard"]),
    dict(slug="bharati-surface-weather", title="Bharati Surface Weather Observations", region="Antarctic",
         data_type="Time series", start=date(2023, 1, 1), end=date(2024, 12, 31), spatial="Bharati, Larsemann Hills",
         description="Three-day surface weather summaries from Bharati. Synthetic demonstration values.",
         variables=[("temperature", "°C", "Air temperature"), ("pressure", "hPa", "Station pressure"),
                    ("wind_speed", "m/s", "Mean wind speed"), ("humidity", "%", "Relative humidity")],
         fmt="CSV", year=2024, gen=lambda r: gen_weather(r, -9, 8, -69.41, 76.19), topics=["polar-meteorology"],
         stations=["bharati"], expeditions=["isea-42"], keywords=["weather", "coastal"]),
    dict(slug="antarctic-total-ozone", title="Antarctic Total Column Ozone", region="Antarctic",
         data_type="Time series", start=date(2021, 1, 1), end=date(2024, 12, 31), spatial="Maitri",
         description="Ground-based total column ozone (sunlit months only), showing the spring ozone-hole dip. Synthetic demonstration values.",
         variables=[("total_ozone", "DU", "Total column ozone in Dobson Units")],
         fmt="CSV", year=2024, gen=gen_ozone, topics=["stratospheric-ozone"], stations=["maitri"],
         expeditions=["isea-42"], keywords=["ozone hole", "Dobson"]),
    dict(slug="southern-ocean-surface-pco2", title="Southern Ocean Surface pCO2 Underway Record", region="Southern Ocean",
         data_type="Time series", start=date(2017, 1, 10), end=date(2017, 3, 10), spatial="Indian Ocean sector, 40°S–60°S",
         description="Underway surface seawater pCO2 with temperature along an expedition track. Synthetic demonstration values.",
         variables=[("pco2", "µatm", "Surface seawater partial pressure of CO2"), ("sst", "°C", "Sea surface temperature")],
         fmt="CSV", year=2017,
         gen=lambda r: gen_simple_series(r, date(2017, 1, 10), date(2017, 3, 10), 1, "pco2", 375, 10, 30, 9, -50.0, 57.5,
                                         extra=lambda t, rr: {"sst": round(float(6 + rr.normal(0, 2)), 2)}),
         topics=["ocean-carbon", "southern-ocean"], stations=[], expeditions=["soe-2017"], keywords=["pCO2", "carbon sink"]),
    dict(slug="southern-ocean-chlorophyll", title="Southern Ocean Chlorophyll Concentration", region="Southern Ocean",
         data_type="Time series", start=date(2017, 1, 10), end=date(2017, 3, 10), spatial="Indian Ocean sector",
         description="Surface chlorophyll concentration as a proxy for phytoplankton biomass. Synthetic demonstration values.",
         variables=[("chlorophyll_a", "mg/m³", "Chlorophyll-a concentration")],
         fmt="CSV", year=2017,
         gen=lambda r: gen_simple_series(r, date(2017, 1, 10), date(2017, 3, 10), 1, "chlorophyll_a", 0.5, 0.25, 20, 0.12,
                                         -55.0, 58.0, floor=0.05),
         topics=["marine-ecosystems", "southern-ocean"], stations=[], expeditions=["soe-2017"], keywords=["phytoplankton", "bloom"]),
    dict(slug="kongsfjorden-mooring-temperature", title="Kongsfjorden Mooring Temperature & Salinity", region="Arctic",
         data_type="Time series", start=date(2019, 1, 1), end=date(2022, 12, 31), spatial="Kongsfjorden, Svalbard",
         description="Mooring time series of water temperature and salinity in an Arctic fjord. Synthetic demonstration values.",
         variables=[("water_temperature", "°C", "Water temperature at mooring depth"), ("salinity", "PSU", "Practical salinity")],
         fmt="NetCDF / CSV", year=2022,
         gen=lambda r: gen_simple_series(r, date(2019, 1, 1), date(2022, 12, 31), 7, "water_temperature", 2.2, 2.0, 245,
                                         0.5, 78.95, 12.0, extra=lambda t, rr: {"salinity": round(float(34.6 + rr.normal(0, 0.15)), 3)}),
         topics=["arctic-fjords", "physical-oceanography"], stations=["indarc", "himadri"], expeditions=["arctic-2019"],
         keywords=["mooring", "Atlantic water"]),
    dict(slug="chandra-basin-glacier-mass-balance", title="Chandra Basin Glacier Mass Balance", region="Himalaya",
         data_type="Annual series", start=date(2015, 1, 1), end=date(2023, 12, 31), spatial="Chandra basin, western Himalaya",
         description="Annual glaciological mass balance for three glaciers. Synthetic demonstration values.",
         variables=[("glacier", "name", "Glacier"), ("mass_balance", "m w.e.", "Annual mass balance in metres water equivalent")],
         fmt="CSV", year=2023, gen=gen_mass_balance, topics=["himalayan-cryosphere", "ice-sheets-glaciers"],
         stations=["himansh"], expeditions=["himalaya-2022"], keywords=["mass balance", "glacier"]),
    dict(slug="ice-core-isotope-record", title="Coastal Ice Core Isotope Record", region="Antarctic",
         data_type="Paleoclimate record", start=date(1800, 1, 1), end=date(2020, 12, 31), spatial="Coastal Dronning Maud Land",
         description="Two-year resolved stable water isotope (δ18O) and accumulation record from a shallow ice core. Synthetic demonstration values.",
         variables=[("year", "year CE", "Age of layer"), ("delta_18O", "‰", "Oxygen isotope ratio"),
                    ("accumulation", "m w.e./yr", "Snow accumulation")],
         fmt="CSV", year=2021, gen=gen_ice_core, topics=["ice-cores-paleoclimate"], stations=["maitri"],
         expeditions=["isea-44"], keywords=["ice core", "isotope"]),
    dict(slug="polar-microbiology-dataset", title="Polar Microbiology Research Dataset", region="Antarctic",
         data_type="Point observations", start=date(2022, 1, 10), end=date(2022, 1, 16), spatial="Schirmacher Oasis lakes",
         description="Lake water chemistry and microbial community indices from replicate samples. Synthetic demonstration values.",
         variables=[("lake", "name", "Lake"), ("conductivity", "µS/cm", "Specific conductivity"),
                    ("nitrate", "mg/L", "Nitrate"), ("cyanobacteria_relative_abundance", "%", "Share of cyanobacterial reads"),
                    ("shannon_diversity", "index", "Shannon diversity index")],
         fmt="CSV", year=2022, gen=gen_microbiology, topics=["polar-microbiology"], stations=["maitri", "schirmacher-lakes-site"],
         expeditions=["isea-20", "isea-44"], keywords=["microbial mats", "lakes"]),
    dict(slug="east-antarctic-glacier-velocity", title="East Antarctic Outlet Glacier Velocity", region="Antarctic",
         data_type="Time series", start=date(2018, 1, 1), end=date(2024, 12, 1), spatial="Coastal Dronning Maud Land",
         description="Monthly surface velocity from satellite feature tracking for two outlet glaciers. Synthetic demonstration values.",
         variables=[("glacier", "name", "Glacier"), ("surface_velocity", "m/yr", "Surface flow speed")],
         fmt="CSV", year=2024, gen=gen_glacier_velocity, topics=["ice-sheets-glaciers", "remote-sensing"],
         stations=["maitri"], expeditions=["isea-44"], keywords=["velocity", "outlet glacier"]),
    dict(slug="arctic-sea-ice-extent-index", title="Arctic September Sea Ice Extent Index", region="Arctic",
         data_type="Annual series", start=date(1990, 1, 1), end=date(2024, 12, 31), spatial="Pan-Arctic",
         description="Teaching index of September sea-ice extent anomaly (unitless). Synthetic demonstration values shaped for classroom use.",
         variables=[("year", "year", "Year"), ("september_extent_anomaly_index", "index", "Standardised anomaly")],
         fmt="CSV", year=2024, gen=gen_arctic_extent, topics=["sea-ice", "climate-change", "science-education"],
         stations=["himadri"], expeditions=[], keywords=["Arctic", "extent", "classroom"]),
    dict(slug="geomagnetic-observations", title="Geomagnetic Field Observations", region="Antarctic",
         data_type="Time series", start=date(2022, 1, 1), end=date(2022, 12, 31), spatial="Bharati",
         description="Geomagnetic H-component variation and Kp-like activity index. Synthetic demonstration values.",
         variables=[("h_component_variation", "nT", "Horizontal component variation"), ("kp_index", "0–9", "Activity index")],
         fmt="CSV", year=2022, gen=gen_geomag, topics=["upper-atmosphere"], stations=["bharati"], expeditions=["isea-42"],
         keywords=["geomagnetic", "storm"]),
    dict(slug="himansh-weather-station", title="Himansh Automatic Weather Station", region="Himalaya",
         data_type="Time series", start=date(2023, 1, 1), end=date(2024, 12, 31), spatial="Chandra basin",
         description="Three-day weather summaries from a high-altitude automatic weather station. Synthetic demonstration values.",
         variables=[("temperature", "°C", "Air temperature"), ("pressure", "hPa", "Station pressure"),
                    ("wind_speed", "m/s", "Mean wind speed"), ("humidity", "%", "Relative humidity")],
         fmt="CSV", year=2024, gen=lambda r: gen_weather(r, -2, -9, 32.4, 77.6), topics=["himalayan-cryosphere", "polar-meteorology"],
         stations=["himansh"], expeditions=["himalaya-2022"], keywords=["AWS", "high altitude"]),
]

# slug, title, media_type, category, region, year, scene, tags, description, links(dict)
MEDIA = [
    ("sea-ice-edge-aerial", "Sea-ice edge in the Prydz Bay sector", "image", "Ice & Glaciers", "Antarctic", 2024, "seaice",
     ["sea ice", "marginal ice zone"], "Broken floes at the edge of the pack, the zone studied in the Antarctic Sea Ice Variability Study.",
     {"documents": ["antarctic-sea-ice-variability-study"], "expeditions": ["isea-43"]}),
    ("pancake-ice-formation", "Pancake ice forming in autumn", "image", "Ice & Glaciers", "Antarctic", 2024, "pancake",
     ["sea ice", "freeze-up"], "Rounded pancakes of young ice — an early stage of autumn freeze-up.",
     {"documents": ["antarctic-sea-ice-variability-study", "how-sea-ice-changes-explainer"]}),
    ("ship-in-marginal-ice-zone", "Expedition vessel in the marginal ice zone", "image", "Expeditions", "Antarctic", 2024, "ship",
     ["ship", "expedition"], "The expedition vessel navigating loose pack ice on the approach to the Larsemann Hills.",
     {"documents": ["antarctic-sea-ice-variability-study", "expedition-43-voyage-report"], "expeditions": ["isea-43"]}),
    ("sea-ice-seasonal-cycle-infographic", "The seasonal cycle of Antarctic sea ice", "infographic", "Outreach", "Antarctic", 2024,
     "info-cycle", ["sea ice", "education"], "Infographic explaining winter growth and summer retreat of Antarctic sea ice.",
     {"documents": ["antarctic-sea-ice-variability-study", "how-sea-ice-changes-explainer"]}),
    ("maitri-station-winter", "Maitri station under winter skies", "image", "Research Stations", "Antarctic", 2023, "station-night",
     ["Maitri", "winter"], "Station buildings on the rocky Schirmacher Oasis during the polar night.",
     {"stations": ["maitri"]}),
    ("bharati-station-coast", "Bharati station on the Larsemann Hills coast", "image", "Research Stations", "Antarctic", 2023,
     "station", ["Bharati", "coast"], "The station on its coastal promontory above the sea ice.", {"stations": ["bharati"]}),
    ("himadri-ny-alesund", "Himadri in Ny-Ålesund", "image", "Research Stations", "Arctic", 2022, "arctic-village",
     ["Himadri", "Svalbard"], "The Arctic research village of Ny-Ålesund with mountains and fjord.", {"stations": ["himadri"]}),
    ("himansh-camp", "High-altitude camp near Himansh", "image", "Research Stations", "Himalaya", 2022, "mountains",
     ["Himansh", "Himalaya"], "Field camp below glacier-covered peaks in the Chandra basin.", {"stations": ["himansh"], "expeditions": ["himalaya-2022"]}),
    ("aurora-australis-over-bharati", "Aurora australis over the coast", "image", "Atmospheric Science", "Antarctic", 2022, "aurora",
     ["aurora", "night sky"], "Green auroral arcs during a geomagnetically active night.",
     {"documents": ["polar-ionosphere-and-aurora"], "stations": ["bharati"]}),
    ("aurora-borealis-svalbard", "Aurora borealis above Svalbard", "image", "Atmospheric Science", "Arctic", 2023, "aurora",
     ["aurora", "Arctic"], "Northern lights over snow-covered mountains.", {"documents": ["aurora-public-explainer"]}),
    ("ozone-balloon-launch", "Ozonesonde balloon launch", "image", "Atmospheric Science", "Antarctic", 2022, "balloon",
     ["ozone", "balloon"], "A balloon carrying an ozone sensor rises into the polar stratosphere.",
     {"documents": ["antarctic-ozone-hole-seasonal-monitoring"], "stations": ["maitri"]}),
    ("aerosol-sampler-ny-alesund", "Aerosol inlet at the Arctic observatory", "image", "Atmospheric Science", "Arctic", 2023, "instrument",
     ["aerosol", "instrument"], "Air inlets and sensors used to sample Arctic aerosols.",
     {"documents": ["arctic-atmospheric-aerosol-observations"], "stations": ["himadri"]}),
    ("adelie-penguins-colony", "Adélie penguins on the shore", "image", "Wildlife", "Antarctic", 2023, "penguins",
     ["penguins", "wildlife"], "A small group of Adélie penguins near the sea ice edge.",
     {"documents": ["emperor-and-adelie-penguins-explainer"]}),
    ("emperor-penguins-sea-ice", "Emperor penguins on winter sea ice", "image", "Wildlife", "Antarctic", 2022, "penguins",
     ["emperor penguin", "sea ice"], "Emperor penguins huddling on stable fast ice.", {"documents": ["emperor-and-adelie-penguins-explainer"]}),
    ("weddell-seal-ice-hole", "Weddell seal resting on fast ice", "image", "Wildlife", "Antarctic", 2021, "seal",
     ["seal", "wildlife"], "A Weddell seal beside a breathing hole in the ice.", {}),
    ("krill-swarm", "Antarctic krill swarm", "image", "Ocean", "Southern Ocean", 2022, "krill",
     ["krill", "food web"], "A dense swarm of krill — a keystone of the Southern Ocean food web.",
     {"documents": ["krill-and-phytoplankton-southern-ocean"]}),
    ("southern-ocean-swell", "Swell of the Southern Ocean", "image", "Ocean", "Southern Ocean", 2024, "ocean",
     ["ocean", "waves"], "Long-period swell typical of the open Southern Ocean.", {"expeditions": ["soe-2024"]}),
    ("ctd-rosette-deployment", "CTD rosette deployment", "image", "Ocean", "Southern Ocean", 2024, "ctd",
     ["CTD", "oceanography"], "A CTD rosette being lowered to measure temperature and salinity profiles.",
     {"documents": ["southern-ocean-oceanographic-observations"], "expeditions": ["soe-2024", "isea-43"]}),
    ("tabular-iceberg", "Tabular iceberg near the ice shelf", "image", "Ice & Glaciers", "Antarctic", 2023, "iceberg",
     ["iceberg", "ice shelf"], "A flat-topped iceberg calved from an Antarctic ice shelf.", {"documents": ["antarctic-cryosphere-monitoring-report"]}),
    ("ice-shelf-front", "Ice shelf front", "image", "Ice & Glaciers", "Antarctic", 2022, "iceshelf",
     ["ice shelf", "glacier"], "The towering front of an ice shelf meeting the ocean.", {"documents": ["antarctic-cryosphere-monitoring-report"]}),
    ("glacier-front-kongsfjorden", "Tidewater glacier in Kongsfjorden", "image", "Ice & Glaciers", "Arctic", 2021, "glacier",
     ["glacier", "fjord"], "A tidewater glacier front discharging into the fjord.", {"documents": ["arctic-fjord-hydrography-kongsfjorden"]}),
    ("chandra-glacier-surface", "Debris-covered glacier surface", "image", "Ice & Glaciers", "Himalaya", 2022, "mountains",
     ["glacier", "Himalaya"], "Rock debris on a glacier surface in the Chandra basin.", {"documents": ["himalayan-glacier-mass-balance"]}),
    ("ice-core-drilling", "Shallow ice-core drilling", "image", "Researchers", "Antarctic", 2024, "drill",
     ["ice core", "fieldwork"], "Researchers extracting a shallow firn core.", {"documents": ["shallow-ice-core-climate-record"], "expeditions": ["isea-44"]}),
    ("lake-sampling-schirmacher", "Lake sampling in the Schirmacher Oasis", "image", "Researchers", "Antarctic", 2022, "lake",
     ["lake", "microbiology"], "Collecting water samples from a freshwater lake.", {"documents": ["polar-microbiology-research-report"]}),
    ("microbial-mat-closeup", "Microbial mat close-up", "image", "Researchers", "Antarctic", 2022, "microscope",
     ["microbiology", "cyanobacteria"], "Layered microbial mat dominated by cyanobacteria.", {"documents": ["polar-microbiology-research-report"]}),
    ("moss-and-lichen", "Mosses and lichens on rock", "image", "Wildlife", "Antarctic", 2020, "lichen",
     ["moss", "lichen"], "Lichens colonising exposed rock in an ice-free area.", {"documents": ["antarctic-mosses-and-lichens"]}),
    ("larsemann-gneiss", "Folded gneiss in the Larsemann Hills", "image", "Antarctica", "Antarctic", 2019, "rocks",
     ["geology", "gneiss"], "Folded metamorphic rock exposed near the coast.", {"documents": ["larsemann-hills-geology"]}),
    ("blizzard-at-maitri", "Blizzard conditions at Maitri", "image", "Antarctica", "Antarctic", 2020, "blizzard",
     ["blizzard", "weather"], "Drifting snow and low visibility during a katabatic-wind blizzard.",
     {"documents": ["katabatic-winds-and-blizzards-maitri"]}),
    ("schirmacher-oasis-panorama", "Schirmacher Oasis panorama", "image", "Antarctica", "Antarctic", 2023, "oasis",
     ["oasis", "landscape"], "Ice-free hills and frozen lakes between the ice sheet and the ice shelf.", {"stations": ["maitri"]}),
    ("polar-night-sky", "Polar night over the ice sheet", "image", "Antarctica", "Antarctic", 2023, "night",
     ["polar night", "stars"], "Midwinter darkness with stars above the ice sheet.", {"documents": ["winter-over-sleep-and-circadian-rhythm"]}),
    ("arctic-tundra-summer", "Arctic tundra in summer", "image", "Arctic", "Arctic", 2023, "tundra",
     ["tundra", "Svalbard"], "Low vegetation and meltwater streams in the Svalbard summer.", {"stations": ["himadri"]}),
    ("svalbard-fjord-panorama", "Kongsfjorden panorama", "image", "Arctic", "Arctic", 2021, "fjord",
     ["fjord", "Arctic"], "Mountains and glaciers framing Kongsfjorden.", {"documents": ["arctic-fjord-hydrography-kongsfjorden"]}),
    ("sea-ice-explainer-video", "How sea ice forms — short explainer", "video", "Outreach", "Antarctic", 2025, "pancake",
     ["sea ice", "education", "video"], "A two-minute explainer on frazil, pancake and pack ice for students.",
     {"documents": ["how-sea-ice-changes-explainer", "antarctic-sea-ice-variability-study"]}),
    ("life-at-maitri-video", "A day at Maitri", "video", "Expeditions", "Antarctic", 2023, "station",
     ["station life", "video"], "Short documentary on daily routines at an Antarctic station.", {"stations": ["maitri"]}),
    ("ship-voyage-video", "Crossing the Southern Ocean", "video", "Expeditions", "Southern Ocean", 2024, "ship",
     ["voyage", "video"], "Time-lapse of the ship crossing Southern Ocean fronts into the pack ice.", {"expeditions": ["isea-43"]}),
    ("aurora-timelapse-video", "Aurora time-lapse", "video", "Atmospheric Science", "Arctic", 2023, "aurora",
     ["aurora", "video"], "Time-lapse of auroral displays over Svalbard.", {"documents": ["aurora-public-explainer"]}),
    ("glacier-fieldwork-video", "Measuring a Himalayan glacier", "video", "Researchers", "Himalaya", 2022, "mountains",
     ["glacier", "fieldwork", "video"], "How glaciologists measure mass balance with stakes and snow pits.",
     {"documents": ["himalayan-glacier-mass-balance"], "expeditions": ["himalaya-2022"]}),
    ("ozone-hole-infographic", "The Antarctic ozone hole explained", "infographic", "Outreach", "Antarctic", 2022, "info-ozone",
     ["ozone", "education"], "Infographic on why the ozone hole forms each spring.", {"documents": ["antarctic-ozone-hole-seasonal-monitoring"]}),
    ("indian-polar-stations-map", "India's polar research stations", "infographic", "Outreach", "Antarctic", 2025, "info-map",
     ["stations", "map"], "Map infographic of Maitri, Bharati, Himadri and Himansh.", {"stations": ["maitri", "bharati", "himadri", "himansh"]}),
    ("southern-ocean-food-web-infographic", "Southern Ocean food web", "infographic", "Outreach", "Southern Ocean", 2022, "info-foodweb",
     ["food web", "krill"], "From phytoplankton to whales: who eats whom.", {"documents": ["krill-and-phytoplankton-southern-ocean"]}),
    ("arctic-vs-antarctic-infographic", "Arctic vs Antarctic", "infographic", "Outreach", "Arctic", 2024, "info-compare",
     ["education", "comparison"], "Key differences between the two polar regions.", {"documents": ["what-is-polar-science", "arctic-sea-ice-decline-review"]}),
    ("winter-over-team", "Winter-over team portrait", "image", "Researchers", "Antarctic", 2021, "team",
     ["team", "station life"], "Members of a winter-over team outside the station.", {"documents": ["winter-over-sleep-and-circadian-rhythm"]}),
    ("station-solar-panels", "Solar panels at a polar station", "image", "Research Stations", "Antarctic", 2024, "solar",
     ["energy", "solar"], "Solar arrays used to reduce diesel consumption in summer.", {"documents": ["station-energy-and-renewables"]}),
]
