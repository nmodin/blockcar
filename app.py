#!/usr/bin/env python3
"""
Blocket Car Scraper - Streamlit UI
Webb-gränssnitt för att söka efter bilar på Blocket och få AI-rekommendationer.
"""

import streamlit as st
from datetime import datetime
from blocket_api import Location
from blockcar import BlocketCarScraper, create_claude_prompt, evaluate_with_claude, CarListing

# Konfigurera sidan
st.set_page_config(
    page_title="Blocket Car Scraper",
    page_icon="🚗",
    layout="wide"
)

# Rubrik
st.title("🚗 Blocket Car Scraper")
st.markdown("Sök efter bilar på Blocket och få AI-drivna rekommendationer från Kodapan")

# Sidebar för filter
st.sidebar.header("🔍 Sökfilter")

# Län-filter (multiselect med sökning)
all_locations = sorted([loc.name.lower().replace("_", " ").title() for loc in Location])
selected_locations = st.sidebar.multiselect(
    "Välj län",
    options=all_locations,
    default=None,
    help="Välj ett eller flera län att söka i (lämna tomt för hela Sverige)"
)

# Pris-filter
st.sidebar.subheader("💰 Pris (SEK)")
col1, col2 = st.sidebar.columns(2)
with col1:
    min_price = st.number_input(
        "Min pris",
        min_value=0,
        max_value=1000000,
        value=20000,
        step=5000
    )
with col2:
    max_price = st.number_input(
        "Max pris",
        min_value=0,
        max_value=1000000,
        value=60000,
        step=5000
    )

# Årsmodell
st.sidebar.subheader("📅 Årsmodell")
min_year = st.sidebar.slider(
    "Minsta årsmodell",
    min_value=2000,
    max_value=datetime.now().year,
    value=2011,
    step=1
)

# Miltal
st.sidebar.subheader("🛣️ Miltal")
col1, col2 = st.sidebar.columns(2)
with col1:
    min_mileage = st.number_input(
        "Min mil",
        min_value=0,
        max_value=50000,
        value=0,
        step=1000
    )
with col2:
    max_mileage = st.number_input(
        "Max mil",
        min_value=0,
        max_value=50000,
        value=30000,
        step=1000
    )

# Övriga filter
st.sidebar.subheader("⚙️ Övriga inställningar")
max_age_days = st.sidebar.slider(
    "Max antal dagar sedan annons lades upp",
    min_value=1,
    max_value=30,
    value=7,
    step=1
)

limit = st.sidebar.slider(
    "Max antal resultat",
    min_value=5,
    max_value=50,
    value=10,
    step=5
)

# AI-utvärdering
use_ai = st.sidebar.checkbox(
    "🤖 Använd Claude AI för att ranka bilar",
    value=True,
    help="Kräver att ANTHROPIC_API_KEY är konfigurerad"
)

# Sökknapp
search_button = st.sidebar.button("🔍 Sök bilar", type="primary", use_container_width=True)

# Huvudinnehåll
if search_button:
    # Konvertera valda län till Location-objekt
    locations = None
    if selected_locations:
        locations = []
        for loc_name in selected_locations:
            # Konvertera tillbaka från display-namn till enum-namn
            enum_name = loc_name.upper().replace(" ", "_")
            try:
                locations.append(Location[enum_name])
            except KeyError:
                st.error(f"Kunde inte hitta län: {loc_name}")
                st.stop()

    # Validera filter
    if min_price > max_price:
        st.error("⚠️ Minsta pris kan inte vara högre än högsta pris!")
        st.stop()

    if min_mileage > max_mileage:
        st.error("⚠️ Minsta miltal kan inte vara högre än högsta miltal!")
        st.stop()

    # Visa sökkriterier
    st.subheader("📍 Söker efter bilar...")
    criteria_cols = st.columns(4)
    with criteria_cols[0]:
        st.metric("Årsmodell", f"{min_year}+")
    with criteria_cols[1]:
        st.metric("Prisintervall", f"{min_price:,}-{max_price:,} SEK")
    with criteria_cols[2]:
        st.metric("Miltal", f"{min_mileage:,}-{max_mileage:,} mil")
    with criteria_cols[3]:
        st.metric("Län", len(selected_locations) if selected_locations else "Hela Sverige")

    # Utför sökning
    with st.spinner("Söker på Blocket..."):
        scraper = BlocketCarScraper()

        try:
            raw_results = scraper.search_cars(
                min_year=min_year,
                min_price=min_price,
                max_price=max_price,
                max_age_days=max_age_days,
                locations=locations,
                limit=limit
            )
        except Exception as e:
            st.error(f"❌ Fel vid sökning: {e}")
            st.info("💡 Tips: Blocket kan blockera förfrågningar från vissa IP-adresser. Prova att köra lokalt på din egen dator.")
            st.stop()

    if not raw_results:
        st.warning("❌ Inga bilar hittades med dessa kriterier. Prova att justera filtren.")
        st.stop()

    # Parsa resultat
    cars = []
    for ad in raw_results:
        car = scraper.parse_car_listing(ad, {})
        # Filtrera på miltal
        if car.mileage:
            if car.mileage < min_mileage or car.mileage > max_mileage:
                continue
        cars.append(car)

    if not cars:
        st.warning("❌ Inga bilar hittades inom det angivna miltalsintervallet.")
        st.stop()

    st.success(f"✅ Hittade {len(cars)} bilar!")

    # Visa resultat
    st.subheader("📊 Sökresultat")

    # AI-utvärdering
    if use_ai:
        with st.spinner("🤖 Claude analyserar bilarna..."):
            prompt = create_claude_prompt(cars)
            evaluation = evaluate_with_claude(prompt)

            if evaluation.startswith("❌"):
                st.error(evaluation)
            else:
                st.subheader("🤖 Claudes Utvärdering")
                st.markdown(evaluation)

                # Sparaknapp för utvärdering
                st.download_button(
                    label="💾 Ladda ner utvärdering",
                    data=evaluation,
                    file_name=f"claude_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )

        st.divider()

    # Visa alla bilar
    st.subheader("🚙 Alla bilar")

    for i, car in enumerate(cars, 1):
        with st.expander(f"**{car.title}** - {car.price:,} SEK"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Pris:** {car.price:,} SEK")
                st.markdown(f"**År:** {car.year or 'N/A'}")
                st.markdown(f"**Miltal:** {f'{car.mileage:,} mil' if car.mileage else 'N/A'}")
                st.markdown(f"**Drivmedel:** {car.fuel_type or 'N/A'}")
                st.markdown(f"**Växellåda:** {car.transmission or 'N/A'}")
                st.markdown(f"**Plats:** {car.location or 'N/A'}")
                st.markdown(f"**Säljare:** {car.seller_type or 'N/A'}")

                st.link_button("🔗 Visa annons på Blocket", car.url)

            with col2:
                if car.images:
                    st.image(car.images[0], use_container_width=True)

else:
    # Välkomstmeddelande
    st.info("👈 Använd filtren i sidofältet och tryck på 'Sök bilar' för att komma igång!")

    st.markdown("""
    ### Hur fungerar det?

    1. **Välj filter** i sidofältet till vänster
    2. **Klicka på Sök bilar** för att starta sökningen
    3. **Få AI-rekommendationer** från Claude (om aktiverat)
    4. **Utforska resultaten** och hitta din drömvil!

    ### Tips:
    - Lämna län tomt för att söka i hela Sverige
    - Aktivera Claude AI för smarta rekommendationer
    - Justera miltalsintervallet för mer exakta resultat
    """)
