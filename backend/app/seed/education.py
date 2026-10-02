"""Learn Polar Science — learning paths and quizzes. Each lesson points to repository resources,
and each quiz explanation cites the resource it is based on."""

LEARNING_PATHS = [
    {
        "level": "beginner", "title": "Beginner — Discover the Poles",
        "description": "What polar regions are, why they matter and how India studies them.",
        "lessons": [
            {"title": "What is polar science?", "summary": "The Arctic is an ocean surrounded by land; Antarctica is a continent surrounded by ocean. Scientists study both because they influence global climate, sea level and ocean circulation.",
             "resources": [("document", "what-is-polar-science"), ("media", "arctic-vs-antarctic-infographic")]},
            {"title": "India's polar stations", "summary": "Maitri and Bharati in Antarctica, Himadri in the Arctic and Himansh in the Himalaya support India's research.",
             "resources": [("station", "maitri"), ("station", "bharati"), ("station", "himadri"), ("media", "indian-polar-stations-map")]},
            {"title": "Life at a polar station", "summary": "Winter-over teams live through months of darkness, isolation and blizzards.",
             "resources": [("document", "winter-over-sleep-and-circadian-rhythm"), ("media", "life-at-maitri-video")]},
            {"title": "Why do we see auroras?", "summary": "Charged particles from the Sun meet the upper atmosphere near the poles and make it glow.",
             "resources": [("document", "aurora-public-explainer"), ("media", "aurora-borealis-svalbard")]},
        ],
    },
    {
        "level": "intermediate", "title": "Intermediate — How the Polar System Works",
        "description": "Sea ice, ozone, glaciers and food webs — the processes behind the headlines.",
        "lessons": [
            {"title": "How does sea ice change?", "summary": "Sea ice forms as frazil and pancake ice, grows into pack ice, and is shaped by winds, ocean heat and temperature.",
             "resources": [("document", "how-sea-ice-changes-explainer"), ("media", "pancake-ice-formation"), ("dataset", "antarctic-sea-ice-observations")]},
            {"title": "The ozone hole", "summary": "Each austral spring, chemistry on polar stratospheric clouds destroys ozone over Antarctica.",
             "resources": [("document", "antarctic-ozone-hole-seasonal-monitoring"), ("media", "ozone-hole-infographic"), ("dataset", "antarctic-total-ozone")]},
            {"title": "Glaciers of the third pole", "summary": "Mass balance tells us whether a glacier is growing or shrinking.",
             "resources": [("document", "himalayan-glacier-mass-balance"), ("dataset", "chandra-basin-glacier-mass-balance")]},
            {"title": "Krill and the food web", "summary": "Phytoplankton feed krill, and krill feed whales, seals and penguins.",
             "resources": [("document", "krill-and-phytoplankton-southern-ocean"), ("media", "southern-ocean-food-web-infographic")]},
        ],
    },
    {
        "level": "advanced", "title": "Advanced — Observations and Evidence",
        "description": "How polar data is collected, analysed and interpreted — with its limitations.",
        "lessons": [
            {"title": "Antarctic sea-ice variability", "summary": "Combining satellites and ship observations to separate the roles of wind, ocean heat and timing.",
             "resources": [("document", "antarctic-sea-ice-variability-study"), ("dataset", "antarctic-sea-ice-observations")]},
            {"title": "Satellite remote sensing of ice", "summary": "Passive microwave, radar, optical imagery and altimetry each see ice differently.",
             "resources": [("document", "satellite-remote-sensing-of-polar-ice")]},
            {"title": "Reading an ice core", "summary": "Water isotopes and annual layers reconstruct past climate.",
             "resources": [("document", "shallow-ice-core-climate-record"), ("dataset", "ice-core-isotope-record")]},
            {"title": "Southern Ocean fronts and carbon", "summary": "Fronts separate water masses; cold water and biology drive carbon uptake.",
             "resources": [("document", "southern-ocean-oceanographic-observations"), ("document", "southern-ocean-carbon-dynamics"), ("dataset", "southern-ocean-ctd-profiles")]},
        ],
    },
]

QUIZZES = {
    "beginner": [
        {"q": "Which statement about the polar regions is correct?",
         "options": ["The Arctic is a continent surrounded by ocean", "Antarctica is a continent surrounded by ocean", "Both are oceans surrounded by land", "Both are continents"],
         "answer": 1, "explain": "Antarctica is a continent surrounded by ocean; the Arctic is an ocean surrounded by land.", "source": "what-is-polar-science"},
        {"q": "Where is India's Arctic research station Himadri located?",
         "options": ["Greenland", "Ny-Ålesund, Svalbard", "Alaska", "Siberia"],
         "answer": 1, "explain": "Himadri is in the international research village of Ny-Ålesund, Svalbard.", "source": "arctic-2007-expedition-summary"},
        {"q": "What produces an aurora?",
         "options": ["Reflection of sunlight on ice", "Charged particles from the Sun colliding with upper-atmosphere gases", "Volcanic eruptions", "Lightning"],
         "answer": 1, "explain": "Auroras form when charged solar particles, guided by Earth's magnetic field, collide with gases in the upper atmosphere.", "source": "aurora-public-explainer"},
    ],
    "intermediate": [
        {"q": "Which is an early stage of sea-ice formation?",
         "options": ["Pack ice", "Icebergs", "Frazil and pancake ice", "Glacier ice"],
         "answer": 2, "explain": "Freezing sea water first forms small frazil crystals, then pancake ice, then a continuous cover.", "source": "how-sea-ice-changes-explainer"},
        {"q": "When does the Antarctic ozone hole develop each year?",
         "options": ["Austral spring", "Austral summer", "Austral autumn", "All year round"],
         "answer": 0, "explain": "Ozone values drop sharply in September–October (austral spring) and recover by December.", "source": "antarctic-ozone-hole-seasonal-monitoring"},
        {"q": "A negative glacier mass balance means…",
         "options": ["The glacier is gaining ice", "The glacier is losing ice", "The glacier is stable", "The glacier is moving faster"],
         "answer": 1, "explain": "Mass balance is gains minus losses; a negative value means the glacier is shrinking.", "source": "himalayan-glacier-mass-balance"},
    ],
    "advanced": [
        {"q": "According to the Antarctic Sea Ice Variability Study, what explains year-to-year differences in the Prydz Bay sector?",
         "options": ["Air temperature alone", "A single dominant factor", "Winds, ocean heat and freeze-up timing acting together", "Ice-shelf collapse"],
         "answer": 2, "explain": "The study concludes that variability arises from the combined action of winds, ocean heat and seasonal timing.", "source": "antarctic-sea-ice-variability-study"},
        {"q": "Why are passive microwave sensors used for daily sea-ice mapping?",
         "options": ["They have the highest resolution", "They see through clouds and darkness", "They measure ice thickness directly", "They are cheapest"],
         "answer": 1, "explain": "Passive microwave radiometers work through clouds and polar night, though at coarse resolution.", "source": "satellite-remote-sensing-of-polar-ice"},
        {"q": "What is a key limitation noted by the sea-ice variability study?",
         "options": ["It used no satellite data", "Statistical relationships are associations, not proof of cause", "It covered every sector of Antarctica", "It measured ice thickness everywhere"],
         "answer": 1, "explain": "The authors note the relationships identified are associations and do not by themselves prove cause and effect.", "source": "antarctic-sea-ice-variability-study"},
    ],
}
