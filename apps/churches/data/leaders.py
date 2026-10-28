"""Area and District superintendents, supplied by the church.

Edit this file if a name changes, then run:  python manage.py import_leaders
(It is safe to run again; it also runs automatically with RUN_IMPORT=1, so the same data loads
on Render, Railway or any other host.)
"""

# (area name, superintendent or None)
AREAS = [
    ("Area 1", "Rev. Dr. Friday Mgboji"),
    ("Area 2", "Rev. Dr. David Ogbosuka JP"),
    ("Area 3", "Rev. Dr. Ezekiel Ogba Igwe"),
    ("Area 4", None),  # no superintendent yet
    ("Area 5", "Rev. Dr. James Anyamnelechi JP"),
    ("Area 6", "Rev. Dr. Uche I. Joel"),
]

# (district name exactly as in the register, superintendent)
DISTRICT_SUPERINTENDENTS = [
    ("Aba District", "Rev. Dr. Uchechukwu E. Okpo"),
    ("Aba East District", "Rev. Dr. Odim Uwa Otaka"),
    ("Aba South East District", "Rev. Dr. Jona Ndukwe"),
    ("Aba South District", "Rev. Dr. Philemon Ibe"),
    ("Izu District", "Rev. Sunday Ndubuisi"),
    ("Umuahia 1 District", "Rev. Sunday Isaac"),
    ("Umuahia 2 District", "Rev. Dr. Nnanna Ukaukwu"),
    ("Okigwe District", "Rev. Dr. Emmanuel Egba"),
    ("Enugu District", "Rev. Dr. Wilson Jombo"),
    ("Uzuakoli District", "Rev. Dr. Okwuchi Jite"),
    ("Abakaliki District", "Rev. Dr. Ikemefuna Edozie"),
    ("Onueke District", "Rev. Dr. John Otta"),
    ("Afikpo District", "Rev. Dr. Godswill Amogu"),
    ("Ikwo District", "Rev. James Uka"),
    ("Alayi District", "Rev. Felix Ogugua"),
    ("Ishieke District", "Rev. Emmanuel Anyaele"),
    ("Ihechiowa District", "Rev. Godspower Oguamalam"),
    ("Edda District", "Rev. Frank Ojukwu"),
    ("Ohafia District", "Rev. Dr. Joseph A. Nkoro"),
    ("Ngbo District", "Rev. Dr. Chinwendu Azu"),
    ("Lagos District", "Rev. Uche Emmanuel"),
    ("Ukwuagba District", "Rev. Dr. Francis Onu"),
    ("Ohaozara District", "Rev. Augustine Okoh"),
    ("Ugwueke District", "Rev. Dr. John Nwaokporo"),
    ("Item District", "Rev. Dr. James Orji"),
    ("Nkpa District", "Rev. John Okwara"),
    ("Port Harcourt District", "Rev. Dr. Israel Ibem"),
    ("Onitsha District", "Rev. Isaac Ukaegbu"),
    ("Gboko District", "Rev. Gabriel Ogwo Uche"),
    ("Cameroon Zone", "Rev. Elijah Kalu"),
    ("Lome Togo District", "Rev. Chinedu Emetu"),
    ("Abuja Zone", "Evangelist Mary Mark"),
    ("Arochukwu Zone", "Rev. Chinedu Chukwu"),
]

# Which districts belong to which Area (district names exactly as in stations.py).
AREA_DISTRICTS = {
    "Area 1": ["Aba District", "Aba South District", "Aba South East District", "Aba East District",
               "Port Harcourt District", "Onitsha District", "Cameroon Zone"],
    "Area 2": ["Umuahia 1 District", "Umuahia 2 District", "Uzuakoli District", "Izu District", "Nkpa District",
               "Alayi District", "Ugwueke District", "Item District", "Okigwe District"],
    "Area 3": ["Ezzamgbo District", "Ngbo District", "Abakaliki District", "Ishieke District",
               "Ukwuagba District", "Enugu District", "Gboko District"],
    "Area 4": ["Lagos District", "Akpakpa District", "Sikecodji District", "Lome Togo District", "Ghana Zone"],
    "Area 5": ["Abiriba District", "Edda District", "Ohafia District", "Ihechiowa District",
               "Nkporo District", "Arochukwu Zone"],
    "Area 6": ["Onueke District", "Ikwo District", "Afikpo District", "Ohaozara District", "Abuja Zone"],
}
