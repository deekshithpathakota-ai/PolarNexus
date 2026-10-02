"""Demo document corpus (PROTOTYPE DEMONSTRATION DATA).

Text is written as plausible, qualitative scientific prose so that search and RAG can be
demonstrated. It does not report real measurements, and the documents are not real publications.
"""

DEMO_SOURCE = "PolarNexus demo corpus (synthetic document)"

FLAGSHIP = dict(
    slug="antarctic-sea-ice-variability-study",
    title="Antarctic Sea Ice Variability Study",
    doc_type="Research Paper",
    region="Antarctic",
    year=2024,
    authors=["ananya-rao", "sana-qureshi", "vikram-menon"],
    institution="Aurora Institute of Polar Studies (demo)",
    topics=["sea-ice", "southern-ocean", "climate-change", "remote-sensing", "polar-meteorology"],
    stations=["bharati", "prydz-bay-site"],
    expeditions=["isea-43"],
    datasets=["antarctic-sea-ice-observations", "southern-ocean-ctd-profiles"],
    media=["sea-ice-edge-aerial", "pancake-ice-formation", "ship-in-marginal-ice-zone", "sea-ice-seasonal-cycle-infographic"],
    keywords=["sea ice extent", "sea-ice concentration", "Southern Annular Mode", "ocean heat", "marginal ice zone", "Prydz Bay"],
    abstract=(
        "Antarctic sea ice grows and retreats every year, covering a vast area of the Southern Ocean at its winter "
        "maximum and shrinking sharply by late summer. This study examines what controls that variability in the "
        "Indian Ocean sector near Prydz Bay by combining satellite sea-ice concentration records, ship-based "
        "observations collected during Antarctic Expedition 43, and surface temperature data. The analysis indicates "
        "that wind patterns, ocean heat below the ice and the timing of autumn freeze-up act together to shape "
        "year-to-year differences, and that no single factor explains the variability on its own."
    ),
    sections=[
        ("Background", 1,
         "Sea ice forms when the surface of the ocean freezes, and around Antarctica it follows a strong seasonal cycle: "
         "it expands through autumn and winter and retreats rapidly in spring and summer. Sea ice matters for climate "
         "because its bright surface reflects much of the incoming sunlight, it limits the exchange of heat and gases "
         "between ocean and atmosphere, and it shapes habitats for algae, krill, penguins and seals. "
         "For several decades the overall extent of Antarctic sea ice changed relatively little compared with the "
         "pronounced decline observed in the Arctic, but the satellite record has since shown several unusually low "
         "years. Understanding why Antarctic sea ice varies so much from year to year is therefore an active research "
         "question, and regional studies are needed because different sectors of the Southern Ocean behave differently."),
        ("Data and Methods", 2,
         "The study combines three sources of evidence. First, daily satellite passive-microwave sea-ice concentration "
         "fields were used to describe the advance and retreat of the ice in the Prydz Bay sector. Second, ship-based "
         "visual ice observations and CTD profiles of temperature and salinity were collected along the ice edge during "
         "the ship transit of Antarctic Expedition 43. Third, surface air temperature and wind records from the coastal "
         "region were used to characterise atmospheric conditions. "
         "Sea-ice concentration is the fraction of an area covered by ice; the ice edge was defined using a commonly "
         "used concentration threshold. Seasonal timing metrics — the dates of autumn advance and spring retreat — were "
         "computed for each year, and their relationship with wind direction, air temperature and upper-ocean "
         "temperature was examined using correlation and composite analysis. The accompanying demonstration dataset "
         "'Antarctic Sea Ice Observations' contains the point observations used in the figures."),
        ("Key Findings", 3,
         "First, wind patterns emerged as a leading influence on regional sea-ice extent: periods of persistent "
         "offshore (southerly) winds pushed the ice edge northward and opened coastal polynyas where new ice formed, "
         "while onshore winds compressed the pack against the coast. "
         "Second, ocean heat below the mixed layer influenced how early the ice could advance in autumn; in years when "
         "warmer subsurface water was mixed upward, freeze-up was delayed and the ice season was shorter. "
         "Third, the timing of autumn freeze-up carried a memory into winter: a late start was often followed by "
         "thinner, less extensive ice in the following months. "
         "Fourth, large-scale atmospheric variability, such as the Southern Annular Mode, modulated the regional winds "
         "and therefore helped explain some — but not all — of the year-to-year differences. "
         "Taken together, the results indicate that Antarctic sea-ice variability in this sector arises from the "
         "combined action of winds, ocean heat and seasonal timing rather than from any single cause."),
        ("Figures", 4,
         "Figure 1 shows the mean seasonal cycle of sea-ice concentration in the Prydz Bay sector, with the shaded "
         "band indicating the range across years. "
         "Figure 2 compares the date of autumn ice advance with the upper-ocean temperature measured before freeze-up, "
         "showing later advance in warmer years. "
         "Figure 3 maps composite wind anomalies during high-ice and low-ice months, illustrating how offshore winds are "
         "associated with a more northerly ice edge. "
         "Figure 4 shows the ship track of Antarctic Expedition 43 across the marginal ice zone together with the "
         "locations of CTD profiles."),
        ("Limitations", 5,
         "The analysis covers one sector of the Southern Ocean and a limited number of years, so the relationships "
         "described here should not be generalised to the whole of Antarctica without further work. Satellite "
         "passive-microwave estimates are less reliable during summer melt and near the coast, and ship observations "
         "were only available along the expedition track. Ice thickness, which is important for the total volume of "
         "sea ice, could not be measured directly in this study. The statistical relationships identified are "
         "associations and do not by themselves prove cause and effect."),
        ("Implications and Outreach Relevance", 6,
         "Because Antarctic sea ice influences the reflection of sunlight, ocean circulation and Southern Ocean "
         "ecosystems, understanding its variability supports better climate projections and ecosystem management. "
         "The study highlights the value of combining satellite records with in-situ observations collected during "
         "expeditions. For students and the public, the central message is that Antarctic sea ice is shaped by "
         "several interacting processes — wind, ocean warmth and seasonal timing — which is why it can change "
         "substantially from one year to the next."),
    ],
)

# Compact definitions for the rest of the corpus: (slug, title, type, region, year, authors, topics,
# stations, expeditions, datasets, abstract, [(section, text), ...])
DOCS = [
    ("southern-ocean-carbon-dynamics", "Southern Ocean Carbon Dynamics", "Research Paper", "Southern Ocean", 2023,
     ["vikram-menon", "priya-bhattacharya"], ["ocean-carbon", "southern-ocean", "marine-ecosystems", "climate-change"],
     [], ["soe-2017"], ["southern-ocean-surface-pco2"],
     "The Southern Ocean is one of the most important regions for the uptake of carbon dioxide from the atmosphere. This "
     "study describes how surface carbon dioxide varies across Southern Ocean fronts in the Indian Ocean sector using "
     "underway measurements and discrete samples collected during a summer expedition.",
     [("Background", "Cold surface waters dissolve carbon dioxide readily, and the overturning circulation of the Southern "
       "Ocean carries absorbed carbon into the deep ocean. Biological production by phytoplankton also draws down carbon "
       "dioxide in summer, while upwelling of carbon-rich deep water can release it."),
      ("Data and Methods", "Surface seawater partial pressure of carbon dioxide (pCO2) was measured continuously along the "
       "ship track together with temperature, salinity and chlorophyll fluorescence. Frontal positions were identified "
       "from temperature and salinity gradients."),
      ("Key Findings", "Surface pCO2 was generally below atmospheric levels south of the Subantarctic Front, indicating "
       "that the ocean was acting as a carbon sink during summer. The lowest values coincided with phytoplankton blooms, "
       "pointing to the role of biological uptake. Near zones of upwelling the sink was weaker."),
      ("Limitations", "Observations represent a single summer season along one ship track and cannot describe winter "
       "conditions, when the balance between uptake and outgassing may differ.")]),
    ("arctic-atmospheric-aerosol-observations", "Arctic Atmospheric Aerosol Observations", "Research Paper", "Arctic", 2023,
     ["meera-iyer"], ["aerosols", "polar-atmosphere", "climate-change"], ["himadri"], ["arctic-2023"],
     ["polar-atmospheric-observations"],
     "Aerosols — tiny particles suspended in air — influence the Arctic climate by scattering and absorbing sunlight and "
     "by affecting clouds. This report summarises aerosol measurements at Ny-Ålesund and discusses the seasonal pattern "
     "of particle concentrations and the contribution of long-range transport.",
     [("Background", "In late winter and spring the Arctic atmosphere often contains pollution transported from lower "
       "latitudes, a phenomenon known as Arctic haze. Black carbon, a light-absorbing component of soot, can warm the "
       "atmosphere and darken snow when deposited."),
      ("Data and Methods", "Particle number concentration, black-carbon mass and meteorological parameters were recorded "
       "continuously. Air-mass back-trajectories were used to identify likely source regions."),
      ("Key Findings", "Aerosol concentrations showed a clear seasonal cycle with higher values in late winter and spring, "
       "consistent with Arctic haze. Episodes of elevated black carbon were associated with air masses arriving from "
       "industrial regions. Summer concentrations were lower, with a larger share of natural marine particles."),
      ("Limitations", "Measurements from a single site may not represent the whole Arctic, and trajectory analysis "
       "identifies likely rather than certain sources.")]),
    ("antarctic-cryosphere-monitoring-report", "Antarctic Cryosphere Monitoring Report", "Technical Report", "Antarctic", 2024,
     ["arjun-desai", "ananya-rao"], ["ice-sheets-glaciers", "sea-ice", "remote-sensing", "climate-change"],
     ["maitri", "bharati"], ["isea-44"], ["east-antarctic-glacier-velocity"],
     "This technical report describes the cryosphere monitoring activities carried out near the Indian Antarctic stations, "
     "including glacier surface velocity, snow accumulation stakes and sea-ice observations, and documents the methods "
     "so that the records can be reused.",
     [("Background", "The Antarctic ice sheet holds most of the world's fresh water. Monitoring how fast its outlet "
       "glaciers flow and how much snow accumulates helps scientists understand its contribution to sea-level change."),
      ("Data and Methods", "Glacier surface velocity was estimated from repeat satellite imagery using feature tracking. "
       "A network of accumulation stakes was measured each summer. Coastal sea-ice conditions were logged visually."),
      ("Key Findings", "The monitored outlet glaciers showed stable flow over the reporting period within measurement "
       "uncertainty. Snow accumulation varied between years and locations, reflecting wind redistribution of snow."),
      ("Limitations", "The period of record is short for detecting trends, and satellite-derived velocities are "
       "uncertain where surface features are sparse.")]),
    ("polar-microbiology-research-report", "Microbial Communities of Schirmacher Oasis Lakes", "Research Paper", "Antarctic", 2022,
     ["kavya-nair"], ["polar-microbiology", "polar-biodiversity"], ["maitri", "schirmacher-lakes-site"], ["isea-20", "isea-44"],
     ["polar-microbiology-dataset"],
     "The freshwater lakes of the Schirmacher Oasis host microbial mats and planktonic communities adapted to cold, "
     "light-limited conditions. This study describes their composition and how it differs between lakes.",
     [("Background", "Antarctic lakes are among the simplest ecosystems on Earth and are dominated by microorganisms such "
       "as cyanobacteria, algae and bacteria. They are useful natural laboratories for studying adaptation to cold."),
      ("Data and Methods", "Water and mat samples were collected from several lakes. Communities were characterised using "
       "DNA sequencing, and water chemistry was measured alongside."),
      ("Key Findings", "Cyanobacteria dominated the microbial mats in most lakes. Community composition differed between "
       "lakes, and these differences were related to water chemistry, particularly nutrient levels and conductivity."),
      ("Limitations", "Sampling took place only in summer; winter communities under thick ice cover could not be studied.")]),
    ("southern-ocean-oceanographic-observations", "Southern Ocean Oceanographic Observations", "Technical Report", "Southern Ocean", 2024,
     ["sana-qureshi"], ["physical-oceanography", "southern-ocean", "sea-ice"], ["prydz-bay-site"], ["soe-2024", "isea-43"],
     ["southern-ocean-ctd-profiles"],
     "This report documents temperature and salinity profiles collected across the Southern Ocean in the Indian Ocean "
     "sector and describes the positions of major fronts during the survey.",
     [("Background", "The Antarctic Circumpolar Current flows eastward around Antarctica and is organised into fronts — "
       "narrow zones where temperature and salinity change sharply. Fronts separate water masses with different properties."),
      ("Data and Methods", "Conductivity-temperature-depth (CTD) profiles were collected at regular intervals along a "
       "meridional transect. Fronts were located using established temperature and salinity criteria."),
      ("Key Findings", "The Subantarctic Front and Polar Front were clearly identified. South of the Polar Front, a cold "
       "subsurface layer known as Winter Water was present, overlain by warmer surface water in summer. Warmer "
       "Circumpolar Deep Water was found beneath the Winter Water, a source of heat that can influence sea ice."),
      ("Limitations", "A single transect gives a snapshot; fronts meander and their positions vary in time.")]),
    ("arctic-fjord-hydrography-kongsfjorden", "Hydrography of Kongsfjorden, Svalbard", "Research Paper", "Arctic", 2021,
     ["aditya-verma", "sana-qureshi"], ["arctic-fjords", "physical-oceanography", "ice-sheets-glaciers"],
     ["himadri", "indarc"], ["arctic-2019"], ["kongsfjorden-mooring-temperature"],
     "Kongsfjorden is an Arctic fjord influenced both by warm Atlantic water from the shelf and by meltwater from "
     "tidewater glaciers. This study uses mooring records and summer CTD surveys to describe how these influences vary.",
     [("Background", "Arctic fjords are sensitive indicators of change because warm Atlantic water can reach glacier fronts "
       "and enhance melting. Kongsfjorden has become a key site for long-term observations."),
      ("Data and Methods", "Temperature and salinity time series from the IndARC mooring were combined with CTD transects "
       "from the fjord mouth to the glacier front collected in summer."),
      ("Key Findings", "Intrusions of Atlantic water raised temperatures in the fjord during some winters, reducing the "
       "formation of local sea ice. Near the glacier front, a fresher surface layer formed from meltwater in summer."),
      ("Limitations", "Mooring data describe conditions at one location and depth range; spatial patterns were inferred "
       "from summer surveys only.")]),
    ("himalayan-glacier-mass-balance", "Glacier Mass Balance in the Chandra Basin", "Research Paper", "Himalaya", 2023,
     ["arjun-desai", "tenzin-norbu"], ["himalayan-cryosphere", "ice-sheets-glaciers", "climate-change"], ["himansh"],
     ["himalaya-2022"], ["chandra-basin-glacier-mass-balance"],
     "Glaciers in the western Himalaya are an important source of water for rivers downstream. This study reports field "
     "measurements of glacier mass balance in the Chandra basin and compares them with satellite estimates.",
     [("Background", "Glacier mass balance is the difference between the snow a glacier gains and the ice and snow it "
       "loses. A negative balance means the glacier is shrinking."),
      ("Data and Methods", "Mass balance was measured with ablation stakes and snow pits using the glaciological method, "
       "and compared with geodetic estimates from satellite elevation data."),
      ("Key Findings", "The benchmark glaciers showed predominantly negative mass balance over the study years, indicating "
       "ice loss. Debris-covered parts of glaciers melted more slowly than clean-ice areas. Field and satellite "
       "estimates agreed in sign but differed in magnitude for some years."),
      ("Limitations", "Stake networks cover only part of each glacier, and access to the upper accumulation zone is limited.")]),
    ("antarctic-ozone-hole-seasonal-monitoring", "Seasonal Monitoring of the Antarctic Ozone Hole", "Technical Report", "Antarctic", 2022,
     ["ishita-banerjee"], ["stratospheric-ozone", "polar-atmosphere"], ["maitri"], ["isea-42"], ["antarctic-total-ozone"],
     "This report describes ground-based total column ozone observations and their seasonal behaviour during the austral "
     "spring, when the Antarctic ozone hole develops.",
     [("Background", "Each austral spring, chemical reactions on polar stratospheric clouds release chlorine that destroys "
       "ozone, creating the Antarctic ozone hole. The Montreal Protocol has reduced the emission of ozone-depleting "
       "substances, and the ozone layer is expected to recover gradually over the coming decades."),
      ("Data and Methods", "Total column ozone was measured with a ground-based spectrometer, and values were compared with "
       "satellite observations for quality control."),
      ("Key Findings", "Ozone values dropped sharply in September and October and recovered in November and December, "
       "following the expected seasonal pattern. Ground and satellite measurements were in good agreement."),
      ("Limitations", "Measurements depend on sunlight and could not be made during the polar night.")]),
    ("polar-ionosphere-and-aurora", "Polar Ionosphere and Auroral Activity", "Research Paper", "Antarctic", 2021,
     ["farhan-siddiqui"], ["upper-atmosphere"], ["bharati", "maitri"], ["isea-42"], ["geomagnetic-observations"],
     "Polar regions are where the Earth's magnetic field lines connect to near-Earth space. This paper describes "
     "ionospheric and geomagnetic observations and their response to solar activity.",
     [("Background", "Charged particles from the Sun are guided by the Earth's magnetic field into the polar upper "
       "atmosphere, producing the aurora and disturbing the ionosphere, which affects radio communication and satellite navigation."),
      ("Data and Methods", "Geomagnetic field variations and ionospheric total electron content were recorded continuously "
       "and analysed during quiet and disturbed periods."),
      ("Key Findings", "Geomagnetic storms produced rapid variations in the magnetic field and irregularities in the "
       "ionosphere. The strongest disturbances were observed during periods of high solar activity."),
      ("Limitations", "Observations from two stations provide limited spatial coverage of a very large region.")]),
    ("krill-and-phytoplankton-southern-ocean", "Krill and Phytoplankton in the Southern Ocean Food Web", "Research Paper", "Southern Ocean", 2022,
     ["priya-bhattacharya", "vikram-menon"], ["marine-ecosystems", "southern-ocean", "sea-ice"], [], ["soe-2017"],
     ["southern-ocean-chlorophyll"],
     "Antarctic krill are a keystone species linking phytoplankton to whales, seals, penguins and fish. This study "
     "examines how phytoplankton distribution relates to krill abundance in the Indian Ocean sector.",
     [("Background", "Phytoplankton blooms in the Southern Ocean are limited by light and by iron. Krill feed on "
       "phytoplankton and on algae growing on the underside of sea ice, so changes in sea ice can affect krill."),
      ("Data and Methods", "Chlorophyll concentration was estimated from water samples and satellite ocean colour. Krill "
       "were sampled with nets at selected stations."),
      ("Key Findings", "Higher chlorophyll concentrations occurred near fronts and in areas influenced by recent sea-ice "
       "melt. Krill were more abundant in areas with higher phytoplankton biomass, supporting the importance of food availability."),
      ("Limitations", "Net sampling captures krill unevenly, and a single season cannot describe interannual variation.")]),
    ("larsemann-hills-geology", "Geology of the Larsemann Hills", "Research Paper", "Antarctic", 2019,
     ["nikhil-joshi"], ["polar-geology"], ["bharati"], ["isea-30"], [],
     "The Larsemann Hills expose ancient metamorphic rocks that record the geological history of East Antarctica. "
     "This paper summarises field mapping around Bharati.",
     [("Background", "East Antarctica contains some of the oldest rocks on Earth. Their study helps reconstruct how "
       "ancient supercontinents assembled and broke apart."),
      ("Data and Methods", "Field mapping, rock sampling and thin-section microscopy were used to classify rock units and "
       "their metamorphic history."),
      ("Key Findings", "The area is dominated by high-grade metamorphic rocks such as gneisses, formed at high temperature "
       "and pressure. The mapped structures are consistent with a history of continental collision."),
      ("Limitations", "Ice and snow cover limit exposure, and dating of the rocks was outside the scope of this study.")]),
    ("shallow-ice-core-climate-record", "A Shallow Ice Core Climate Record from Coastal Dronning Maud Land", "Research Paper", "Antarctic", 2021,
     ["rohan-kulkarni"], ["ice-cores-paleoclimate", "climate-change", "ice-sheets-glaciers"], ["maitri"], ["isea-44"],
     ["ice-core-isotope-record"],
     "Ice cores preserve layers of snow that record past climate. This study analyses a shallow core from coastal "
     "Dronning Maud Land to examine variations in temperature-related isotopes and snow accumulation over recent centuries.",
     [("Background", "The ratio of heavy to light water isotopes in snow is related to the temperature at which it formed, "
       "so isotope records in ice cores act as a proxy for past temperature."),
      ("Data and Methods", "The core was sampled at high resolution and analysed for stable water isotopes and major ions. "
       "Annual layers were identified using seasonal chemical signals."),
      ("Key Findings", "The isotope record showed decadal variability, and snow accumulation increased in recent decades "
       "relative to the earlier part of the record. Volcanic sulphate peaks helped confirm the dating."),
      ("Limitations", "Coastal cores are influenced by local wind and moisture sources, so they may not reflect regional "
       "climate fully.")]),
    ("katabatic-winds-and-blizzards-maitri", "Katabatic Winds and Blizzards at Maitri", "Technical Report", "Antarctic", 2020,
     ["meera-iyer"], ["polar-meteorology", "polar-atmosphere"], ["maitri"], ["isea-10", "isea-40"], ["maitri-surface-weather"],
     "Strong winds flowing down the Antarctic ice sheet shape weather at coastal stations. This report characterises "
     "katabatic wind events and blizzards recorded at Maitri.",
     [("Background", "Katabatic winds form when cold, dense air over the ice sheet flows downslope under gravity. They "
       "can be persistent and strong, and when they carry snow they cause blizzards with very low visibility."),
      ("Data and Methods", "Surface wind, temperature, pressure and visibility from the station weather observatory were "
       "analysed to identify blizzard events."),
      ("Key Findings", "The prevailing wind direction was from the ice sheet towards the coast, consistent with katabatic "
       "flow. Blizzards were most frequent in winter and were associated with passing low-pressure systems."),
      ("Limitations", "Visibility observations are partly subjective, and data gaps occurred during instrument maintenance.")]),
    ("winter-over-sleep-and-circadian-rhythm", "Sleep and Circadian Rhythm During the Antarctic Winter", "Research Paper", "Antarctic", 2022,
     ["neha-kapoor"], ["polar-medicine"], ["maitri", "bharati"], ["isea-40"], [],
     "Members of winter-over teams experience months of continuous darkness and isolation. This study describes changes "
     "in sleep patterns and wellbeing and evaluates simple countermeasures.",
     [("Background", "Light is the main signal that keeps the body's internal clock aligned. Without sunlight during the "
       "polar night, sleep timing can drift and sleep quality can decline."),
      ("Data and Methods", "Volunteers wore activity monitors and completed sleep diaries and wellbeing questionnaires "
       "throughout the winter."),
      ("Key Findings", "Sleep onset tended to occur later during mid-winter, and self-reported sleep quality decreased. "
       "Structured daily routines and bright-light exposure in the morning were associated with more regular sleep."),
      ("Limitations", "Small group sizes limit statistical power, and results may depend on individual circumstances.")]),
    ("station-waste-management-practices", "Waste Management Practices at Antarctic Stations", "Technical Report", "Antarctic", 2023,
     ["karthik-reddy"], ["environmental-protection", "polar-logistics"], ["maitri", "bharati"], ["isea-42"], [],
     "Environmental protection is a core obligation of Antarctic operations. This report describes waste handling, "
     "segregation and removal practices at the Indian stations.",
     [("Background", "The Protocol on Environmental Protection to the Antarctic Treaty sets rules for waste management, "
       "requiring most waste to be removed from the Antarctic Treaty area."),
      ("Data and Methods", "Waste streams were audited over a season, and handling procedures were documented."),
      ("Key Findings", "Segregation at source improved the share of waste suitable for compaction and removal. Food waste "
       "and wastewater required treatment before disposal or removal according to regulations."),
      ("Limitations", "Audit results represent one season and depend on station occupancy.")]),
    ("station-energy-and-renewables", "Energy Systems and Renewable Options for Polar Stations", "Technical Report", "Antarctic", 2024,
     ["karthik-reddy"], ["polar-logistics", "environmental-protection"], ["bharati", "maitri"], [], [],
     "Polar stations depend heavily on diesel fuel transported over long distances. This report reviews the energy "
     "demand of stations and the potential role of solar and wind power.",
     [("Background", "Reducing fuel use lowers logistical costs and environmental risk from fuel spills."),
      ("Data and Methods", "Station electrical loads were analysed and compared with the seasonal availability of solar "
       "and wind resources."),
      ("Key Findings", "Solar power can contribute substantially in summer but not in winter darkness, while wind power is "
       "available year-round but requires robust turbines. A hybrid system with storage offers the most reliable reduction in fuel use."),
      ("Limitations", "The analysis is a feasibility review and does not include detailed cost estimates.")]),
    ("arctic-sea-ice-decline-review", "Arctic Sea Ice Decline: A Review for Educators", "Educational Resource", "Arctic", 2024,
     ["lakshmi-subramanian", "ananya-rao"], ["sea-ice", "climate-change", "science-education", "remote-sensing"],
     ["himadri"], [], ["arctic-sea-ice-extent-index"],
     "This educational resource explains, in accessible language, how and why Arctic sea ice has declined since satellite "
     "monitoring began, and suggests classroom activities.",
     [("Background", "Satellites have monitored Arctic sea ice continuously since the late 1970s. The September minimum "
       "extent has declined markedly over this period, and the remaining ice is younger and thinner than before."),
      ("Key Concepts", "The ice-albedo feedback explains part of the decline: as bright ice melts, darker ocean absorbs "
       "more sunlight, which warms the water and causes more melting."),
      ("Classroom Activities", "Students can compare satellite maps from different years, plot an extent index and discuss "
       "why the Arctic and Antarctic behave differently."),
      ("Limitations", "This resource simplifies complex processes for teaching purposes.")]),
    ("what-is-polar-science", "What Is Polar Science? An Introduction", "Educational Resource", "Antarctic", 2025,
     ["lakshmi-subramanian"], ["science-education", "climate-change"], ["maitri", "bharati", "himadri"], [], [],
     "An introductory guide to polar science for school students: what the polar regions are, why scientists study them, "
     "and how India conducts research in the Arctic, Antarctic and Himalaya.",
     [("Background", "The polar regions are the areas around the North and South Poles. The Arctic is an ocean surrounded "
       "by land, while Antarctica is a continent surrounded by ocean."),
      ("Why It Matters", "Polar regions influence global climate, sea level and ocean circulation. Ice cores from Antarctica "
       "contain air bubbles that record past atmospheres."),
      ("India in the Polar Regions", "India conducts research at Maitri and Bharati in Antarctica, at Himadri in the Arctic "
       "and at Himansh in the Himalaya, through annual expeditions coordinated by the national polar research centre."),
      ("Limitations", "This is an introductory overview and does not cover any topic in depth.")]),
    ("how-sea-ice-changes-explainer", "How Does Sea Ice Change? An Explainer", "Educational Resource", "Antarctic", 2025,
     ["lakshmi-subramanian", "ananya-rao"], ["sea-ice", "science-education"], [], [], ["antarctic-sea-ice-observations"],
     "An intermediate-level explainer describing how sea ice forms, grows and melts, and what makes it vary between years.",
     [("Background", "When sea water cools to about minus two degrees Celsius it begins to freeze, first forming small "
       "crystals called frazil ice, then pancake ice, and eventually a continuous ice cover."),
      ("What Controls Sea Ice", "Air temperature, winds, ocean currents and the heat stored in the ocean all influence how "
       "much sea ice forms. Winds can push ice away from the coast or pile it up."),
      ("Arctic vs Antarctic", "Arctic sea ice is surrounded by land and some of it survives several summers, while most "
       "Antarctic sea ice melts each summer."),
      ("Limitations", "Simplified for learners; see the Antarctic Sea Ice Variability Study for research detail.")]),
    ("expedition-43-voyage-report", "Antarctic Expedition 43 — Voyage and Science Summary", "Expedition Report", "Antarctic", 2024,
     ["sana-qureshi", "ananya-rao"], ["sea-ice", "southern-ocean", "polar-logistics"], ["bharati", "prydz-bay-site"],
     ["isea-43"], ["antarctic-sea-ice-observations", "southern-ocean-ctd-profiles"],
     "A demonstration expedition report summarising the ship voyage, science programmes and data collected during "
     "Antarctic Expedition 43, with emphasis on sea-ice and ocean observations near the Larsemann Hills.",
     [("Voyage Summary", "The ship crossed the Southern Ocean fronts and entered the marginal ice zone before reaching the "
       "coast near Bharati. Ice conditions were logged hourly during transit through the pack."),
      ("Science Programmes", "Programmes included sea-ice visual observations, CTD profiling, aerosol sampling and "
       "resupply of station instruments."),
      ("Data Collected", "Ship-based sea-ice observations and CTD profiles were archived and later used in the Antarctic "
       "Sea Ice Variability Study."),
      ("Limitations", "Weather and ice conditions limited the number of planned ocean stations.")]),
    ("expedition-1-historical-overview", "India's First Antarctic Expedition — Historical Overview", "Expedition Report", "Antarctic", 2021,
     ["lakshmi-subramanian"], ["polar-logistics", "science-education"], ["dakshin-gangotri"], ["isea-1", "isea-3"], [],
     "An outreach overview of India's first expedition to Antarctica in 1981–82 and the establishment of the first Indian "
     "base in the following seasons.",
     [("Background", "India's first expedition to Antarctica sailed in December 1981 under the leadership of Dr S. Z. "
       "Qasim and reached the Antarctic coast in January 1982."),
      ("Significance", "The expedition demonstrated the capability to reach and work in Antarctica and marked the start "
       "of India's Antarctic research programme. The first Indian base, Dakshin Gangotri, was set up during the third expedition."),
      ("Legacy", "Later stations, Maitri and Bharati, enabled year-round research. Annual expeditions have continued since."),
      ("Limitations", "This overview is for outreach; consult official NCPOR records for authoritative historical detail.")]),
    ("arctic-2007-expedition-summary", "First Indian Arctic Expedition — Summary", "Expedition Report", "Arctic", 2008,
     ["meera-iyer", "kavya-nair"], ["polar-microbiology", "polar-atmosphere"], ["himadri"], ["arctic-2007"], [],
     "A summary of India's first scientific expedition to the Arctic in 2007 and the research directions it opened in Svalbard.",
     [("Background", "India's first Arctic expedition took place in 2007, with scientists working in Ny-Ålesund, Svalbard."),
      ("Research Focus", "Initial work covered atmospheric science, microbiology and glaciology."),
      ("Outcome", "The expedition led to the establishment of the Indian Arctic research station Himadri in 2008."),
      ("Limitations", "Demonstration summary; details beyond the expedition year and station outcome are illustrative.")]),
    ("southern-ocean-pilot-expedition-summary", "Pilot Expedition to the Southern Ocean — Summary", "Expedition Report", "Southern Ocean", 2005,
     ["sana-qureshi"], ["southern-ocean", "physical-oceanography"], [], ["soe-2004"], [],
     "A demonstration summary of India's pilot expedition to the Southern Ocean in 2004 and the observational programme it began.",
     [("Background", "The Southern Ocean connects the Atlantic, Indian and Pacific Oceans and plays a central role in "
       "global ocean circulation."),
      ("Programme", "The pilot expedition collected hydrographic and biological observations in the Indian Ocean sector."),
      ("Outcome", "It established a basis for regular Southern Ocean expeditions."),
      ("Limitations", "Demonstration summary; details are illustrative.")]),
    ("polar-science-outreach-highlights-2024", "Polar Science Outreach Highlights 2024", "News / Outreach", "Antarctic", 2024,
     ["lakshmi-subramanian"], ["science-education", "climate-change"], ["maitri", "bharati", "himadri"], ["isea-43"], [],
     "A demonstration outreach digest describing school talks, exhibitions and online explainers on polar science.",
     [("Highlights", "Researchers returning from the Antarctic delivered talks to students about life at a polar station "
       "and the science of sea ice."),
      ("Digital Outreach", "Short explainers on sea ice, ozone and krill were prepared for social media and reviewed by scientists before publication."),
      ("Lessons", "Visual stories and question-and-answer sessions were the most engaging formats for school audiences."),
      ("Limitations", "Demonstration outreach record.")]),
    ("aurora-public-explainer", "Why Do We See Auroras? A Public Explainer", "News / Outreach", "Arctic", 2023,
     ["farhan-siddiqui", "lakshmi-subramanian"], ["upper-atmosphere", "science-education"], ["himadri"], [], [],
     "A plain-language explainer about the aurora borealis and aurora australis and how scientists study them.",
     [("What Is an Aurora", "Auroras are lights in the sky produced when charged particles from the Sun collide with gases "
       "in the upper atmosphere, guided by the Earth's magnetic field towards the poles."),
      ("Colours", "Green light commonly comes from oxygen, while red and purple can come from oxygen at higher altitude and from nitrogen."),
      ("Why Scientists Care", "The same processes that create auroras can disturb radio communication and satellite navigation."),
      ("Limitations", "Simplified explanation for the public.")]),
    ("permafrost-in-the-western-himalaya", "Permafrost in the Western Himalaya", "Research Paper", "Himalaya", 2024,
     ["tenzin-norbu"], ["permafrost", "himalayan-cryosphere"], ["himansh"], ["himalaya-2022"], [],
     "Mountain permafrost is widespread but poorly mapped in the Himalaya. This study uses ground temperature loggers to "
     "assess where permafrost is likely to occur in the Chandra basin.",
     [("Background", "Permafrost is ground that stays frozen for at least two consecutive years. In mountains, its thawing "
       "can destabilise slopes and affect water resources."),
      ("Data and Methods", "Ground surface temperature loggers were installed at different elevations and aspects, and "
       "annual mean temperatures were calculated."),
      ("Key Findings", "Ground temperatures indicated that permafrost is likely at higher elevations and on shaded, "
       "north-facing slopes. Snow cover timing strongly influenced ground temperature."),
      ("Limitations", "Loggers measure near-surface temperatures; deeper boreholes would be needed to confirm permafrost.")]),
    ("satellite-remote-sensing-of-polar-ice", "Satellite Remote Sensing of Polar Ice — Methods Overview", "Technical Report", "Antarctic", 2023,
     ["ananya-rao"], ["remote-sensing", "sea-ice", "ice-sheets-glaciers"], [], [], ["antarctic-sea-ice-observations"],
     "A methods overview describing the main satellite techniques used to observe sea ice and ice sheets: passive "
     "microwave, synthetic aperture radar, optical imagery and altimetry.",
     [("Passive Microwave", "Passive microwave radiometers can see through clouds and darkness, making them suitable for "
       "daily sea-ice concentration mapping, though at coarse resolution."),
      ("Radar and Optical", "Synthetic aperture radar provides high-resolution images regardless of light, while optical "
       "imagery is intuitive but limited by clouds and polar night."),
      ("Altimetry", "Satellite altimeters measure surface height, which can be used to estimate ice-sheet elevation change "
       "and sea-ice freeboard, from which thickness can be derived."),
      ("Limitations", "Each technique has trade-offs in resolution, coverage and sensitivity to melt conditions.")]),
    ("antarctic-mosses-and-lichens", "Mosses and Lichens of the Schirmacher Oasis", "Research Paper", "Antarctic", 2020,
     ["kavya-nair"], ["polar-biodiversity"], ["maitri"], ["isea-20"], [],
     "Ice-free areas of Antarctica support simple plant communities of mosses and lichens. This study documents their "
     "distribution around the Schirmacher Oasis.",
     [("Background", "Only a small fraction of Antarctica is free of ice, and these areas host mosses, lichens and "
       "microscopic animals adapted to cold and dryness."),
      ("Data and Methods", "Vegetation plots were surveyed, and species were identified from collected specimens."),
      ("Key Findings", "Lichens were the most widespread group, occurring on exposed rock, while mosses were concentrated "
       "near meltwater sources. Moisture availability was the main factor controlling distribution."),
      ("Limitations", "Survey coverage was limited to accessible areas.")]),
    ("emperor-and-adelie-penguins-explainer", "Penguins of East Antarctica — Learning Resource", "Educational Resource", "Antarctic", 2023,
     ["priya-bhattacharya", "lakshmi-subramanian"], ["polar-biodiversity", "sea-ice", "science-education"], [], [], [],
     "A learning resource about Adélie and emperor penguins, their reliance on sea ice and the ocean, and how scientists observe them.",
     [("Background", "Adélie and emperor penguins are true Antarctic species. Emperor penguins breed on stable sea ice "
       "during winter, while Adélie penguins nest on ice-free ground in summer."),
      ("Food and Sea Ice", "Both species depend on the ocean for food such as krill and fish, and changes in sea ice can "
       "affect their breeding and feeding."),
      ("How Scientists Observe", "Scientists use colony counts, tagging and satellite images to monitor penguin populations."),
      ("Limitations", "Learning resource; not a research publication.")]),
    ("polar-data-management-guidelines", "Polar Data Management and Metadata Guidelines", "Technical Report", "Antarctic", 2025,
     ["karthik-reddy", "ananya-rao"], ["environmental-protection", "science-education"], ["ncpor-goa"], [], [],
     "Guidelines for describing, archiving and sharing polar research data so that it remains discoverable and reusable.",
     [("Background", "Polar data is expensive to collect, and good metadata ensures it can be found and reused for decades."),
      ("Recommendations", "Each dataset should include a title, abstract, spatial and temporal coverage, variables with "
       "units, methods, contacts, licence and a persistent identifier."),
      ("Data Sharing", "Data should be shared in open, documented formats through a recognised data centre after quality control."),
      ("Limitations", "Demonstration guidance aligned with common metadata practice; not an official standard.")]),
    ("internal-draft-black-carbon-on-snow", "Black Carbon on Snow at Ny-Ålesund (Internal Draft)", "Research Paper", "Arctic", 2025,
     ["meera-iyer", "kavya-nair"], ["aerosols", "polar-atmosphere"], ["himadri"], ["arctic-2023"], ["polar-atmospheric-observations"],
     "Internal draft (restricted visibility) examining black carbon deposited on snow and its potential effect on snow albedo.",
     [("Background", "Black carbon deposited on snow darkens the surface and can accelerate melting."),
      ("Data and Methods", "Snow samples were filtered and analysed for black carbon content."),
      ("Preliminary Findings", "Concentrations were low on average with occasional higher values after haze episodes."),
      ("Limitations", "Preliminary internal draft; results not yet peer reviewed.")]),
]
