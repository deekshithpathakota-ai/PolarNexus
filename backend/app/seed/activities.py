"""Demo corpus — institutional activities (workshops, outreach, briefings, announcements, achievements).

Every activity here is PROTOTYPE DEMONSTRATION DATA (is_demo=True). Organisers are the fictional demo
institutions used elsewhere in the corpus; venues are generic city names, never a claim that a real institution
held the event. Each activity is linked to existing demo records so the repository reads as one ecosystem.
"""
from datetime import date, timedelta

DEMO_ORGS = {
    "aurora": "Aurora Institute of Polar Studies (demo)",
    "konkan": "Konkan Ocean Sciences Institute (demo)",
    "deccan": "Deccan Centre for Atmospheric Research (demo)",
    "himalayan": "Himalayan Cryosphere Laboratory (demo)",
    "outreach": "PolarNexus Outreach Programme (demo)",
}

CITY = {
    "goa": ("Goa (demo venue)", 15.49, 73.82, "India"),
    "hyderabad": ("Hyderabad (demo venue)", 17.385, 78.487, "India"),
    "pune": ("Pune (demo venue)", 18.52, 73.857, "India"),
    "dehradun": ("Dehradun (demo venue)", 30.316, 78.032, "Himalaya"),
    "bengaluru": ("Bengaluru (demo venue)", 12.972, 77.594, "India"),
    "delhi": ("New Delhi (demo venue)", 28.614, 77.209, "India"),
    "online": ("Online webinar", None, None, "India"),
    "maitri": ("Maitri station, Schirmacher Oasis", -70.7667, 11.7333, "Antarctic"),
    "himadri": ("Himadri station, Ny-Ålesund", 78.9167, 11.9333, "Arctic"),
    "bharati": ("Bharati station, Larsemann Hills", -69.4068, 76.1953, "Antarctic"),
}


def activities(today: date) -> list[dict]:
    """Returns activity specs. Two are scheduled relative to `today` so the demo always has upcoming events."""
    return [
        dict(slug="sea-ice-teachers-workshop-2025", title="Teaching Antarctic Sea Ice: Workshop for School Teachers",
             activity_type="workshop", date=date(2025, 7, 18), end_date=date(2025, 7, 19), city="goa",
             organisation=DEMO_ORGS["aurora"], department="Education & Outreach Cell", audience="School science teachers",
             featured=True, cover_scene="seaice", status="completed",
             description=("A two-day hands-on workshop that walked secondary-school teachers through the sea-ice "
                          "seasonal cycle using the repository's sea-ice explainer, the Antarctic Sea Ice Variability "
                          "Study and the synthetic sea-ice observation dataset. Teachers practised reading time-series "
                          "charts and turning research summaries into classroom explanations."),
             outcomes=["Classroom lesson outline built from the student explainer",
                       "Teachers practised reading the sea-ice dataset charts",
                       "Feedback collected on the Learn Polar Science pathway"],
             researchers=["ananya-rao", "lakshmi-subramanian"], expeditions=["isea-43"], stations=["bharati"],
             documents=["antarctic-sea-ice-variability-study", "how-sea-ice-changes-explainer"],
             datasets=["antarctic-sea-ice-observations"], media=["sea-ice-explainer-video", "sea-ice-seasonal-cycle-infographic"],
             topics=["sea-ice", "science-education"]),
        dict(slug="expedition-44-pre-departure-briefing", title="Antarctic Expedition 44: Pre-departure Science Briefing",
             activity_type="expedition_briefing", date=date(2024, 10, 22), city="goa",
             organisation=DEMO_ORGS["aurora"], department="Expedition Planning (demo)", audience="Expedition members and partner scientists",
             cover_scene="ship", status="completed",
             description=("Briefing for members of the demonstration Expedition 44 covering the season's science "
                          "programme, station logistics at Maitri and Bharati, field safety and the data-management "
                          "guidelines that every team follows when submitting observations to the repository."),
             outcomes=["Science programme and sampling plan reviewed", "Data-management checklist issued to every team"],
             researchers=["rohan-kulkarni", "neha-kapoor"], expeditions=["isea-44"], stations=["maitri", "bharati"],
             documents=["polar-data-management-guidelines", "expedition-43-voyage-report"], media=["ship-voyage-video"],
             topics=["polar-logistics"]),
        dict(slug="southern-ocean-carbon-seminar", title="Seminar: How the Southern Ocean Takes Up Carbon",
             activity_type="seminar", date=date(2024, 3, 14), city="online",
             organisation=DEMO_ORGS["konkan"], department="Ocean Biogeochemistry Group (demo)", audience="Researchers and graduate students",
             cover_scene="ocean", status="completed",
             description=("An online research seminar presenting the demonstration Southern Ocean carbon study, the "
                          "surface pCO2 and chlorophyll datasets, and observations from the Southern Ocean Expedition "
                          "2024 voyage. The talk focused on methods and on the limitations stated in the study."),
             outcomes=["Recorded seminar linked to the carbon study", "Questions on sampling coverage logged for the team"],
             researchers=["vikram-menon", "priya-bhattacharya"], expeditions=["soe-2024"], stations=["ncpor-goa"],
             documents=["southern-ocean-carbon-dynamics", "krill-and-phytoplankton-southern-ocean"],
             datasets=["southern-ocean-surface-pco2", "southern-ocean-chlorophyll"], media=["southern-ocean-swell", "ctd-rosette-deployment"],
             topics=["ocean-carbon", "southern-ocean"]),
        dict(slug="polar-science-exhibition-2025", title="From the Poles to the Public: Polar Science Exhibition",
             activity_type="exhibition", date=date(2025, 11, 5), end_date=date(2025, 11, 12), city="bengaluru",
             organisation=DEMO_ORGS["outreach"], department="Public Engagement", audience="General public and families",
             featured=True, cover_scene="aurora", status="completed",
             description=("A week-long public exhibition built from repository media: station photographs, aurora "
                          "time-lapses, infographics on the ozone hole and the Southern Ocean food web, and a "
                          "walk-through of how a research finding becomes a reviewed outreach post."),
             outcomes=["Exhibition panels generated from approved outreach content", "Visitor questions fed into the AI assistant examples"],
             researchers=["lakshmi-subramanian", "karthik-reddy"], stations=["maitri", "bharati", "himadri"],
             documents=["polar-science-outreach-highlights-2024", "aurora-public-explainer"],
             media=["aurora-timelapse-video", "ozone-hole-infographic", "southern-ocean-food-web-infographic", "indian-polar-stations-map"],
             topics=["science-education", "upper-atmosphere"]),
        dict(slug="school-outreach-hyderabad-ozone", title="School Outreach: What Happens to the Ozone Layer over Antarctica?",
             activity_type="school_outreach", date=date(2025, 9, 16), city="hyderabad",
             organisation=DEMO_ORGS["deccan"], department="Atmospheric Science Outreach (demo)", audience="Students, grades 8–10",
             cover_scene="balloon", status="completed",
             description=("A school visit explaining the seasonal Antarctic ozone hole with the ozone infographic, the "
                          "balloon-launch photographs and a simplified reading of the ozone monitoring report. "
                          "Students compared the synthetic total-ozone dataset across seasons."),
             outcomes=["Student explainer drafted in the Content Studio", "Quiz from the Learn pathway used in class"],
             researchers=["meera-iyer", "ishita-banerjee"], stations=["maitri"],
             documents=["antarctic-ozone-hole-seasonal-monitoring"], datasets=["antarctic-total-ozone"],
             media=["ozone-balloon-launch", "ozone-hole-infographic"], topics=["stratospheric-ozone", "science-education"]),
        dict(slug="arctic-aerosols-public-lecture", title="Public Lecture: What Is Floating in the Arctic Air?",
             activity_type="public_lecture", date=date(2024, 8, 29), city="pune",
             organisation=DEMO_ORGS["deccan"], department="Aerosol Research Group (demo)", audience="General public",
             cover_scene="arctic-village", status="completed",
             description=("An evening public lecture on Arctic aerosol observations near Himadri in Ny-Ålesund, using "
                          "the aerosol observation report and the polar atmospheric observations dataset, with "
                          "photographs of the aerosol sampler."),
             outcomes=["Lecture slides linked to the aerosol report", "Plain-language summary submitted for review"],
             researchers=["meera-iyer", "farhan-siddiqui"], expeditions=["arctic-2023"], stations=["himadri"],
             documents=["arctic-atmospheric-aerosol-observations"], datasets=["polar-atmospheric-observations"],
             media=["aerosol-sampler-ny-alesund", "himadri-ny-alesund"], topics=["aerosols", "polar-atmosphere"]),
        dict(slug="himalayan-cryosphere-training", title="Training Programme: Glacier Mass-Balance Field Methods",
             activity_type="training_programme", date=date(2023, 6, 12), end_date=date(2023, 6, 23), city="dehradun",
             organisation=DEMO_ORGS["himalayan"], department="Field Methods Unit (demo)", audience="Early-career researchers",
             cover_scene="mountains", status="completed",
             description=("A two-week training programme on stake and pit measurements, data logging and quality "
                          "control for glacier mass-balance work, linked to the Chandra Basin Glacier Campaign and the "
                          "glacier mass-balance study. Participants submitted practice records using the repository's "
                          "metadata guidelines."),
             outcomes=["Practice datasets submitted with complete metadata", "Field safety checklist revised"],
             researchers=["arjun-desai", "tenzin-norbu"], expeditions=["himalaya-2022"], stations=["himansh"],
             documents=["himalayan-glacier-mass-balance", "permafrost-in-the-western-himalaya", "polar-data-management-guidelines"],
             datasets=["chandra-basin-glacier-mass-balance", "himansh-weather-station"],
             media=["glacier-fieldwork-video", "chandra-glacier-surface", "himansh-camp"], topics=["himalayan-cryosphere", "ice-sheets-glaciers"]),
        dict(slug="polar-data-stewardship-conference", title="Polar Data Stewardship & Open Science Conference",
             activity_type="conference", date=date(2025, 2, 20), end_date=date(2025, 2, 21), city="delhi",
             organisation=DEMO_ORGS["aurora"], department="Data Management Office (demo)", audience="Data managers, researchers, librarians",
             cover_scene="instrument", status="completed",
             description=("A two-day conference on metadata, provenance and open-data practice for polar research, "
                          "including a session demonstrating how PolarNexus records the source, licence and "
                          "verification status of every record."),
             outcomes=["Provenance field list agreed for the repository", "Licensing guidance for uploaded media drafted"],
             researchers=["neha-kapoor", "rohan-kulkarni", "aditya-verma"],
             documents=["polar-data-management-guidelines", "satellite-remote-sensing-of-polar-ice"],
             topics=["remote-sensing", "environmental-protection"]),
        dict(slug="maitri-winter-science-briefing", title="Winter-over Science Briefing from Maitri",
             activity_type="research_announcement", date=date(2024, 6, 21), city="maitri",
             organisation=DEMO_ORGS["aurora"], department="Station Science Office (demo)", audience="Researchers and the public (live stream)",
             cover_scene="station-night", status="completed",
             description=("A mid-winter update from the demonstration winter-over team at Maitri describing ongoing "
                          "surface weather observations, blizzard conditions and the sleep and circadian-rhythm "
                          "study carried out during the polar night."),
             outcomes=["Mid-season data summary posted to the repository", "Public Q&A questions answered with citations"],
             researchers=["rohan-kulkarni", "kavya-nair"], expeditions=["isea-43"], stations=["maitri"],
             documents=["katabatic-winds-and-blizzards-maitri", "winter-over-sleep-and-circadian-rhythm"],
             datasets=["maitri-surface-weather"], media=["maitri-station-winter", "blizzard-at-maitri", "winter-over-team"],
             topics=["polar-meteorology", "polar-medicine"]),
        dict(slug="krill-awareness-campaign", title="Awareness Campaign: Why Tiny Krill Matter",
             activity_type="awareness_campaign", date=date(2025, 4, 22), end_date=date(2025, 5, 22), city="online",
             organisation=DEMO_ORGS["outreach"], department="Digital Outreach", audience="Social-media audiences",
             cover_scene="krill", status="completed",
             description=("A month-long social-media campaign built from editor-approved outreach posts about krill, "
                          "phytoplankton and the Southern Ocean food web. Every post linked back to the source study "
                          "and passed an evidence check before publication."),
             outcomes=["Campaign posts traced to the krill and phytoplankton study", "All posts approved by an editor before release"],
             researchers=["sana-qureshi", "lakshmi-subramanian"], expeditions=["soe-2017"],
             documents=["krill-and-phytoplankton-southern-ocean"], datasets=["southern-ocean-chlorophyll"],
             media=["krill-swarm", "southern-ocean-food-web-infographic"], topics=["marine-ecosystems", "science-education"]),
        dict(slug="arctic-station-anniversary", title="Milestone: Arctic Research Programme Review Meeting",
             activity_type="achievement", date=date(2023, 7, 1), city="himadri",
             organisation=DEMO_ORGS["aurora"], department="Arctic Programme Office (demo)", audience="Programme scientists",
             cover_scene="fjord", status="completed",
             description=("A review meeting for the demonstration Arctic programme summarising fjord hydrography, "
                          "mooring observations from the IndARC observatory record and glacier-front studies in "
                          "Kongsfjorden, and setting priorities for the next summer campaign."),
             outcomes=["Programme priorities recorded", "Kongsfjorden datasets cross-linked to publications"],
             researchers=["aditya-verma", "priya-bhattacharya"], expeditions=["arctic-2019", "arctic-2023"], stations=["himadri", "indarc"],
             documents=["arctic-fjord-hydrography-kongsfjorden", "arctic-sea-ice-decline-review"],
             datasets=["kongsfjorden-mooring-temperature"], media=["glacier-front-kongsfjorden", "svalbard-fjord-panorama"],
             topics=["arctic-fjords", "physical-oceanography"]),
        dict(slug="repository-launch-announcement", title="Announcement: Polar Knowledge Repository Opens for Researcher Uploads",
             activity_type="institutional_announcement", date=date(2026, 1, 15), city="online",
             organisation=DEMO_ORGS["outreach"], department="Platform Team", audience="Researchers and institutions",
             cover_scene="night", status="completed",
             description=("Announcement that researchers can upload documents, images and videos to the prototype "
                          "repository. Uploads are validated, indexed for search and labelled as user-uploaded until "
                          "an administrator verifies their provenance."),
             outcomes=["Upload guidelines published", "Verification workflow enabled for administrators"],
             researchers=["neha-kapoor"], documents=["polar-data-management-guidelines"], topics=["science-education"]),
        dict(slug="ice-core-open-day", title="Open Day: How Ice Remembers Past Climate",
             activity_type="official_event", date=today + timedelta(days=24), city="goa",
             organisation=DEMO_ORGS["aurora"], department="Paleoclimate Laboratory (demo)", audience="Students and the public",
             cover_scene="drill", status="upcoming",
             description=("A planned open day at the demonstration paleoclimate laboratory introducing ice-core "
                          "drilling, the shallow ice-core climate record and the isotope dataset, with guided "
                          "explanations for school groups."),
             outcomes=[], researchers=["nikhil-joshi"], expeditions=["isea-40"],
             documents=["shallow-ice-core-climate-record"], datasets=["ice-core-isotope-record"],
             media=["ice-core-drilling"], topics=["ice-cores-paleoclimate", "science-education"]),
        dict(slug="aurora-webinar-upcoming", title="Webinar: The Science Behind the Polar Lights",
             activity_type="public_lecture", date=today + timedelta(days=41), city="online",
             organisation=DEMO_ORGS["deccan"], department="Upper Atmosphere Group (demo)", audience="General public",
             cover_scene="aurora", status="upcoming",
             description=("An upcoming public webinar on the ionosphere and aurora, drawing on the polar ionosphere "
                          "study, geomagnetic observations and aurora photographs from Bharati and Svalbard."),
             outcomes=[], researchers=["farhan-siddiqui"], stations=["bharati"],
             documents=["polar-ionosphere-and-aurora", "aurora-public-explainer"], datasets=["geomagnetic-observations"],
             media=["aurora-australis-over-bharati", "aurora-borealis-svalbard"], topics=["upper-atmosphere"]),
    ]
