# 🚗 Blocket Car Scraper

Söker automatiskt efter bilar på Blocket.se och använder Claude AI för att ranka de bästa köpen baserat på pris, årsmodell, miltal och annonstext.

---

## Förutsättningar

- Python 3.10 eller nyare
- Ett [Anthropic-konto](https://console.anthropic.com) med API-nyckel (för AI-utvärdering)

---

## Installation

### 1. Klona repot

```bash
git clone https://github.com/ditt-användarnamn/blocket-car-scraper.git
cd blocket-car-scraper
```

### 2. Skapa och aktivera en virtuell miljö

```bash
python3 -m venv venv
source venv/bin/activate
```

> **OBS:** Du behöver aktivera venv varje gång du öppnar en ny terminal:
> ```bash
> source venv/bin/activate
> ```

### 3. Installera beroenden

```bash
pip install anthropic
pip install blocket-api
pip install python-dotenv
```

---

## Skaffa en Claude API-nyckel

1. Gå till [console.anthropic.com](https://console.anthropic.com)
2. Logga in eller skapa ett konto
3. Klicka på **"API Keys"** i vänstermenyn
4. Klicka på **"Create Key"** och kopiera nyckeln direkt — den visas bara en gång

### Konfigurera API-nyckeln

**Metod 1: Använd .env fil (Rekommenderat)**

Skapa en `.env` fil i projektmappen:

```bash
cp .env.example .env
```

Öppna `.env` och klistra in din API-nyckel:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Metod 2: Sätt som miljövariabel**

Tillfälligt (gäller bara nuvarande session):
```bash
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

Permanent:
```bash
echo "export ANTHROPIC_API_KEY='sk-ant-api03-...'" >> ~/.zshrc
source ~/.zshrc
```

> ⚠️ Dela aldrig din API-nyckel eller lägg in den i Git. `.env` filen är redan exkluderad i `.gitignore`.

---

## Användning

### Testa med exempeldata (kräver ingen inloggning på Blocket)

```bash
python3 blockcar.py --demo
```

### Testa med exempeldata + AI-utvärdering

```bash
python3 blockcar.py --demo --evaluate
```

### Riktig sökning på Blocket

```bash
python3 blockcar.py
```

### Riktig sökning med AI-utvärdering

```bash
python3 blockcar.py --evaluate
```

---

## Flaggor och inställningar

| Flagga | Standard | Beskrivning |
|---|---|---|
| `--demo` | — | Kör med exempeldata istället för Blocket |
| `--evaluate` | — | Skickar resultaten till Claude för AI-bedömning |
| `--min-year` | 2011 | Minsta årsmodell |
| `--min-price` | 20000 | Lägsta pris i SEK |
| `--max-price` | 60000 | Högsta pris i SEK |
| `--max-age` | 1 | Max antal dagar sedan annonsen lades upp |
| `--limit` | 10 | Max antal annonser att hämta |
| `--location` | — | Filtrera på län (använd komma för flera) |

### Exempel med egna inställningar

Sök i Stockholm och Uppsala:
```bash
python3 blockcar.py --location stockholm,uppsala --evaluate
```

Sök i Skåne med anpassade priser:
```bash
python3 blockcar.py --location skane --min-year 2013 --min-price 30000 --max-price 70000 --max-age 3 --limit 15 --evaluate
```

### Tillgängliga län

`stockholm`, `uppsala`, `sodermanland`, `ostergotland`, `jonkoping`, `kronoberg`, `kalmar`, `gotland`, `blekinge`, `skane`, `halland`, `vastra_gotaland`, `varmland`, `orebro`, `vastmanland`, `dalarna`, `gavleborg`, `vasternorrland`, `jamtland`, `vasterbotten`, `norrbotten`

---

## Resultat

Scriptet skapar tre filer när det körs:

| Fil | Innehåll |
|---|---|
| `blocket_results.json` | Rådata från sökningen |
| `claude_prompt.md` | Prompten som skickas till Claude |
| `claude_evaluation.md` | Claudes bedömning (om `--evaluate` används) |

---

## Licens

MIT
