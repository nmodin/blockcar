#!/usr/bin/env python3
"""
Blocket Car Scraper
Söker efter bilar på Blocket.se och förbereder data för AI-bedömning.
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv

from blocket_api import BlocketAPI, CarAd, CarSortOrder, Location

# Ladda miljövariabler från .env fil
load_dotenv()


def evaluate_with_claude(prompt: str) -> str:
    """Skickar prompten till Claude för utvärdering."""
    try:
        import anthropic
    except ImportError:
        return "❌ Saknar anthropic-paketet. Installera med: pip install anthropic"
   
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "❌ Saknar ANTHROPIC_API_KEY. Skapa en .env fil med:\n   ANTHROPIC_API_KEY=sk-ant-api03-...\n   Eller sätt miljövariabeln: export ANTHROPIC_API_KEY='din-nyckel'"
   
    client = anthropic.Anthropic(api_key=api_key)
   
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
   
    return message.content[0].text


@dataclass
class CarListing:
    """Strukturerad bilannons för analys."""
    id: str
    title: str
    price: int
    year: Optional[int]
    mileage: Optional[int]
    fuel_type: Optional[str]
    transmission: Optional[str]
    engine_power: Optional[int]
    location: Optional[str]
    seller_type: Optional[str]
    description: Optional[str]
    url: str
    images: list[str]
    published_date: Optional[str]
   
    def to_assessment_prompt(self) -> str:
        """Formaterar bildata för Claude-bedömning."""
        return f"""
## {self.title}
- **Pris:** {self.price:,} SEK
- **Årsmodell:** {self.year or 'Ej angivet'}
- **Miltal:** {f'{self.mileage:,} mil' if self.mileage else 'Ej angivet'}
- **Drivmedel:** {self.fuel_type or 'Ej angivet'}
- **Växellåda:** {self.transmission or 'Ej angivet'}
- **Motoreffekt:** {f'{self.engine_power} hk' if self.engine_power else 'Ej angivet'}
- **Plats:** {self.location or 'Ej angivet'}
- **Säljartyp:** {self.seller_type or 'Ej angivet'}
- **Annons-URL:** {self.url}

**Beskrivning:**
{self.description or 'Ingen beskrivning tillgänglig.'}
""".strip()


class BlocketCarScraper:
    """Scraper för bilannonser på Blocket."""
   
    def __init__(self):
        self.api = BlocketAPI()
   
    def search_cars(
        self,
        min_year: int = 2011,
        min_price: int = 20000,
        max_price: int = 60000,
        max_age_days: int | None = None,
        locations: list[Location] | None = None,
        sort_order: CarSortOrder = CarSortOrder.PUBLISHED_DESC,
        limit: int = 20
    ) -> list[dict]:
        """
        Söker efter bilar med givna filter.
       
        Args:
            min_year: Minsta årsmodell (standard: 2011)
            min_price: Lägsta pris i SEK (standard: 20000)
            max_price: Högsta pris i SEK (standard: 60000)
            max_age_days: Max antal dagar sedan annonsen publicerades (None = ingen gräns)
            locations: Lista med platser att söka i (standard: hela Sverige)
            sort_order: Sorteringsordning
            limit: Max antal resultat
           
        Returns:
            Lista med bilannonser (rådata från API)
        """
        search_params = {
            "price_from": min_price,
            "price_to": max_price,
            "year_from": min_year,
            "sort_order": sort_order,
        }
       
        if locations:
            search_params["locations"] = locations
       
        results = self.api.search_car(**search_params)
       
        ads = results.get("docs", [])
       
        # Filtrera på annonsålder om angivet
        if max_age_days is not None:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            filtered_ads = []
            for ad in ads:
                # Nytt format använder timestamp i millisekunder
                timestamp = ad.get("timestamp")
                if timestamp:
                    try:
                        pub_date = datetime.fromtimestamp(timestamp / 1000)
                        if pub_date >= cutoff_date:
                            filtered_ads.append(ad)
                    except (ValueError, TypeError):
                        # Om vi inte kan parsa, inkludera annonsen ändå
                        filtered_ads.append(ad)
                else:
                    # Ingen timestamp, inkludera ändå
                    filtered_ads.append(ad)
            ads = filtered_ads
       
        return ads[:limit]
   
    def get_car_details(self, ad_id: int) -> dict:
        """Hämtar detaljerad information om en specifik bilannons."""
        try:
            details = self.api.get_ad(CarAd(ad_id))
            return details
        except Exception as e:
            print(f"Kunde inte hämta detaljer för annons {ad_id}: {e}")
            return {}
   
    def parse_car_listing(self, ad_data: dict, details: dict = None) -> CarListing:
        """Parsar rådata till strukturerad CarListing."""
       
        ad_id = ad_data.get("ad_id") or ad_data.get("id", "")
       
        # Nytt API-format har fälten direkt på objektet
        price_data = ad_data.get("price", {})
        price = price_data.get("amount") or price_data.get("value", 0)
       
        # Extrahera från detaljer om tillgängligt
        description = ""
        images = []
        if details:
            description = details.get("body", "")
            images = [img.get("url", "") for img in details.get("images", [])]
       
        # Hämta bild-URL om tillgänglig
        image_data = ad_data.get("image", {})
        if image_data and image_data.get("url"):
            images = [image_data.get("url")]
       
        # Hantera organisation/säljare
        org_name = ad_data.get("organisation_name")
        seller_type = f"Handlare ({org_name})" if org_name else "Privatperson"
       
        # Canonical URL eller konstruera från ID
        url = ad_data.get("canonical_url") or f"https://www.blocket.se/annons/{ad_id}"
       
        return CarListing(
            id=str(ad_id),
            title=ad_data.get("heading") or ad_data.get("subject", "Okänd bil"),
            price=price,
            year=ad_data.get("year"),
            mileage=ad_data.get("mileage"),
            fuel_type=ad_data.get("fuel"),
            transmission=ad_data.get("transmission"),
            engine_power=ad_data.get("engine_power"),
            location=ad_data.get("location", ""),
            seller_type=seller_type,
            description=description,
            url=url,
            images=images,
            published_date=self._parse_timestamp(ad_data.get("timestamp"))
        )
   
    def _parse_timestamp(self, timestamp: int | None) -> Optional[str]:
        """Konverterar millisekund-timestamp till datumstring."""
        if timestamp:
            try:
                dt = datetime.fromtimestamp(timestamp / 1000)
                return dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass
        return None
   



def create_claude_prompt(cars: list[CarListing]) -> str:
    """
    Skapar en prompt för Claude att bedöma bilarna.
   
    Args:
        cars: Lista med CarListing-objekt
       
    Returns:
        Formaterad prompt för Claude
    """
    car_descriptions = "\n\n---\n\n".join(
        car.to_assessment_prompt() for car in cars
    )
   
    prompt = f"""Jag letar efter en begagnad bil och har hittat följande {len(cars)} annonser på Blocket.
Kan du hjälpa mig bedöma dessa bilar och ranka de 3 bästa köpen?

För varje bil i din top 3, ge mig:
1. **Prisvärdhet** (1-5): Är priset rimligt för årsmodell, miltal och skick?
2. **Potentiella risker**: Vad bör jag vara uppmärksam på med just denna modell/årgång?
3. **Frågor att ställa säljaren**: Vad bör jag fråga innan köp?

Här är bilarna:

{car_descriptions}

---

Avsluta med en tydlig ranking:
🥇 **Bästa köpet:** [Bil] - [Kort motivering]
🥈 **Näst bästa:** [Bil] - [Kort motivering]  
🥉 **Tredje plats:** [Bil] - [Kort motivering]
"""
    return prompt


def main():
    """Huvudfunktion för att köra scrapern."""
    import argparse
   
    parser = argparse.ArgumentParser(description="Sök efter bilar på Blocket")
    parser.add_argument("--demo", action="store_true", help="Kör med exempeldata")
    parser.add_argument("--evaluate", action="store_true", help="Skicka till Claude för utvärdering (kräver ANTHROPIC_API_KEY)")
    parser.add_argument("--max-age", type=int, default=1, help="Max antal dagar sedan annons publicerades (standard: 1)")
    parser.add_argument("--min-year", type=int, default=2011, help="Minsta årsmodell (standard: 2011)")
    parser.add_argument("--min-price", type=int, default=20000, help="Lägsta pris i SEK (standard: 20000)")
    parser.add_argument("--max-price", type=int, default=60000, help="Högsta pris i SEK (standard: 60000)")
    parser.add_argument("--limit", type=int, default=10, help="Max antal resultat (standard: 10)")
    args = parser.parse_args()
   
    print("🚗 Blocket Car Scraper")
    print("=" * 50)
   
    scraper = BlocketCarScraper()
   
    # Sök efter bilar med dina kriterier
    print("\n📍 Söker efter bilar...")
    print("   Kriterier:")
    print(f"   - Årsmodell: {args.min_year} och nyare")
    print(f"   - Pris: {args.min_price:,} - {args.max_price:,} SEK")
    print(f"   - Annons max {args.max_age} dag{'ar' if args.max_age != 1 else ''} gammal")
   
    if args.demo:
        print("\n⚠️  Kör i DEMO-läge med exempeldata")
        raw_results = get_demo_data()
    else:
        try:
            raw_results = scraper.search_cars(
                min_year=args.min_year,
                min_price=args.min_price,
                max_price=args.max_price,
                max_age_days=args.max_age,
                limit=args.limit
            )
        except Exception as e:
            print(f"\n❌ Fel vid sökning: {e}")
            print("\n💡 Tips:")
            print("   - Blocket kan blockera förfrågningar från vissa IP-adresser")
            print("   - Kör scriptet lokalt på din egen dator")
            print("   - Använd --demo för att se exempelutdata")
            print("\n   Exempel: python blocket_car_scraper.py --demo")
            return
   
    if not raw_results:
        print("\n❌ Inga bilar hittades med dessa kriterier.")
        return
   
    print(f"\n✅ Hittade {len(raw_results)} bilar")
   
    # Parsa och strukturera resultaten
    cars: list[CarListing] = []
   
    print("\n📋 Hämtar detaljerad information...")
    for i, ad in enumerate(raw_results, 1):
        ad_id = ad.get("ad_id")
        print(f"   [{i}/{len(raw_results)}] Hämtar annons {ad_id}...")
       
        # Hämta detaljerad info (valfritt - kan ta tid)
        # details = scraper.get_car_details(ad_id)
        details = {}  # Skippa detaljhämtning för snabbhet
       
        car = scraper.parse_car_listing(ad, details)
        cars.append(car)
   
    # Visa sammanfattning
    print("\n" + "=" * 50)
    print("📊 SÖKRESULTAT")
    print("=" * 50)
   
    for car in cars:
        print(f"\n🚙 {car.title}")
        print(f"   Pris: {car.price:,} SEK")
        print(f"   År: {car.year or 'N/A'} | Mil: {car.mileage or 'N/A'}")
        print(f"   {car.seller_type}")
        print(f"   🔗 {car.url}")
   
    # Spara rådata till JSON
    output_data = {
        "search_timestamp": datetime.now().isoformat(),
        "search_criteria": {
            "min_year": args.min_year,
            "min_price": args.min_price,
            "max_price": args.max_price,
            "max_age_days": args.max_age
        },
        "results_count": len(cars),
        "cars": [asdict(car) for car in cars]
    }
   
    with open("blocket_results.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print("\n💾 Rådata sparad till: blocket_results.json")
   
    # Skapa Claude-prompt
    claude_prompt = create_claude_prompt(cars)
   
    with open("claude_prompt.md", "w", encoding="utf-8") as f:
        f.write(claude_prompt)
    print("📝 Claude-prompt sparad till: claude_prompt.md")
   
    # Utvärdera med Claude eller visa prompten
    if args.evaluate:
        print("\n" + "=" * 50)
        print("🤖 CLAUDES UTVÄRDERING")
        print("=" * 50)
        print("\nSkickar till Claude för analys...")
       
        evaluation = evaluate_with_claude(claude_prompt)
       
        print("\n" + evaluation)
       
        # Spara utvärderingen
        with open("claude_evaluation.md", "w", encoding="utf-8") as f:
            f.write(evaluation)
        print("\n💾 Utvärdering sparad till: claude_evaluation.md")
    else:
        print("\n" + "=" * 50)
        print("🤖 PROMPT FÖR CLAUDE")
        print("=" * 50)
        print("\nKopiera texten nedan och klistra in i Claude:\n")
        print("-" * 50)
        print(claude_prompt[:2000])
        if len(claude_prompt) > 2000:
            print(f"\n... [Trunkerad - se claude_prompt.md för full text] ...")
        print("-" * 50)
        print("\n💡 Tips: Kör med --evaluate för automatisk utvärdering")


def get_demo_data() -> list[dict]:
    """Returnerar exempeldata för demo-läge (nytt API-format)."""
    now = datetime.now()
   
    return [
        {
            "ad_id": "12345678",
            "id": "12345678",
            "heading": "Volvo V60 2.0 D4 Momentum",
            "price": {"amount": 54900},
            "location": "Stockholm",
            "year": 2015,
            "mileage": 12500,
            "fuel": "Diesel",
            "transmission": "Automat",
            "organisation_name": None,
            "canonical_url": "https://www.blocket.se/mobility/item/12345678",
            "timestamp": int((now - timedelta(hours=2)).timestamp() * 1000)
        },
        {
            "ad_id": "87654321",
            "id": "87654321",
            "heading": "Volkswagen Golf 1.4 TSI Style",
            "price": {"amount": 42500},
            "location": "Göteborg",
            "year": 2014,
            "mileage": 9800,
            "fuel": "Bensin",
            "transmission": "Manuell",
            "organisation_name": "Bilhuset AB",
            "canonical_url": "https://www.blocket.se/mobility/item/87654321",
            "timestamp": int((now - timedelta(hours=5)).timestamp() * 1000)
        },
        {
            "ad_id": "11223344",
            "id": "11223344",
            "heading": "Toyota Auris 1.8 Hybrid Active",
            "price": {"amount": 38000},
            "location": "Malmö",
            "year": 2013,
            "mileage": 14200,
            "fuel": "Hybrid",
            "transmission": "Automat",
            "organisation_name": None,
            "canonical_url": "https://www.blocket.se/mobility/item/11223344",
            "timestamp": int((now - timedelta(days=1)).timestamp() * 1000)
        },
        {
            "ad_id": "55667788",
            "id": "55667788",
            "heading": "Ford Focus 1.0 EcoBoost Titanium",
            "price": {"amount": 29900},
            "location": "Uppsala",
            "year": 2012,
            "mileage": 16500,
            "fuel": "Bensin",
            "transmission": "Manuell",
            "organisation_name": None,
            "canonical_url": "https://www.blocket.se/mobility/item/55667788",
            "timestamp": int((now - timedelta(days=1, hours=3)).timestamp() * 1000)
        },
        {
            "ad_id": "99887766",
            "id": "99887766",
            "heading": "Skoda Octavia 1.4 TSI Ambition",
            "price": {"amount": 47500},
            "location": "Linköping",
            "year": 2016,
            "mileage": 8900,
            "fuel": "Bensin",
            "transmission": "DSG",
            "organisation_name": "Skoda Center",
            "canonical_url": "https://www.blocket.se/mobility/item/99887766",
            "timestamp": int((now - timedelta(hours=12)).timestamp() * 1000)
        },
    ]


if __name__ == "__main__":
    main()


