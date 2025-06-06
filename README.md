# AutoCal - System automatycznego zarządzania planem zajęć

Automatyczne zarządzanie planem zajęć z integracją Google Calendar wykorzystujące architekturę mikroserwisów Docker.

## 🚀 Funkcjonalności

- ✅ Automatyczny eksport planu zajęć do Google Calendar
- ✅ Integracja harmonogramu wydziałowego z planem studenta
- ✅ Architektura mikroserwisów z Worker Pattern
- ✅ Skalowalne kontenery Docker
- ✅ Interfejs CLI z prostymi komendami

## 🏗️ Architektura

System składa się z 6 kontenerów Docker:

- **CLI** - Interfejs wiersza poleceń
- **Processor** - Główny serwer API (FastAPI)
- **Data-Prepare Worker** - Przetwarzanie harmonogramu
- **Google Calendar Worker** - Integracja z Google API
- **MongoDB** - Baza danych konfiguracji
- **Redis** - System kolejek

## 📋 Wymagania

- Docker & Docker Compose
- Dostęp do `credentials.json` (Google OAuth - **skontaktuj się z właścicielem projektu**)
- Pliki JSON: `schedule.json` (harmonogram wydziałowy), `timetable.json` (plan zajęć)

## 🛠️ Instalacja i uruchomienie

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/hallu-boss/AutoCal.git
cd AutoCal
```

### 2. Pozyskanie credentials.json

⚠️ **WAŻNE**: Aby system działał prawidłowo, musisz poprosić właściciela projektu o plik `credentials.json` zawierający dane aplikacji Google OAuth.

Umieść plik w katalogu: `cli/credentials.json`

### 3. Przygotowanie plików danych

Umieść swoje pliki w katalogu `cli/data/`:

- `schedule.json` - harmonogram wydziałowy
- `timetable.json` - plan zajęć studenta

### 4. Uruchomienie systemu

```bash
# Uruchomienie wszystkich serwisów (bez CLI)
docker-compose up -d

# Sprawdzenie statusu kontenerów
docker-compose ps
```

### 5. Konfiguracja CLI

```bash
# Uruchomienie kontenera CLI
docker-compose --profile cli run --rm cli bash

# W kontenerze CLI wykonaj:
# 1. Autoryzacja Google OAuth
python cli.py register

# 2. Konfiguracja systemu
python cli.py config

# 3. Eksport planu zajęć
python cli.py export
```

## 📖 Użytkowanie

### Dostępne komendy CLI

#### `register` - Autoryzacja Google

```bash
python cli.py register
```

- Otwiera przeglądarkę na localhost:2255
- Autoryzuje aplikację w Google OAuth
- Zapisuje token do `token.json`

#### `config` - Konfiguracja systemu

```bash
python cli.py config
```

- Uploaduje pliki: `token.json`, `schedule.json`, `timetable.json`
- Waliduje JSON względem schematów
- Zwraca `config_id` i zapisuje w `config_id.pkl`

#### `export` - Eksport do Google Calendar

```bash
# Aktualny tydzień
python cli.py export

# Następny tydzień
python cli.py export -o 1

# Poprzedni tydzień
python cli.py export -o -1
```

### Przykładowy workflow

```bash
# 1. Uruchomienie systemu
docker-compose up -d

# 2. Wejście do CLI
docker-compose --profile cli run --rm cli bash

# 3. Pierwszy raz - pełna konfiguracja
python cli.py register    # Autoryzacja Google
python cli.py config      # Upload plików JSON
python cli.py export      # Eksport aktualnego tygodnia

# 4. Kolejne eksporty
python cli.py export -o 1  # Następny tydzień
```

## 🔧 Konfiguracja zaawansowana

### Skalowanie worker'ów

```bash
# Więcej worker'ów dla wydajności
docker-compose up -d --scale data-prepare=3 --scale google=2
```

### Porty serwisów

- **Processor API**: `localhost:8000`
- **MongoDB**: `localhost:27017`
- **Redis**: `localhost:6379`
- **CLI OAuth**: `localhost:2255`

### Logi systemowe

```bash
# Wszystkie serwisy
docker-compose logs -f

# Konkretny serwis
docker-compose logs -f processor
docker-compose logs -f data-prepare
```

## 📂 Struktura plików

```
AutoCal/
├── cli/                    # Kontener CLI
│   ├── cli.py             # Program główny
│   ├── data/              # Pliki JSON
│   │   ├── schedule.json  # Harmonogram wydziałowy
│   │   └── timetable.json # Plan zajęć studenta
│   ├── credentials.json   # ⚠️ Google OAuth (od właściciela)
│   └── Dockerfile
├── processor/             # API Server
│   ├── app/
│   │   ├── processor.py   # FastAPI server
│   │   └── planvalidation/ # Walidacja JSON
│   └── Dockerfile
├── data-prepare/          # Worker przetwarzania
│   ├── worker.py
│   └── Dockerfile
├── gcal-api/             # Google Calendar Worker
│   ├── worker.py
│   ├── gcalendar/        # Biblioteka Google API
│   └── Dockerfile
├── shared/               # Wspólna biblioteka
│   ├── constants.py
│   ├── types.py
│   └── worker.py
└── docker-compose.yaml
```

## 🐛 Rozwiązywanie problemów

### Brak credentials.json

```
❌ Błąd: [Errno 2] No such file or directory: 'credentials.json'
```

**Rozwiązanie**: Skontaktuj się z właścicielem projektu o plik `credentials.json`

### Błędy autoryzacji Google

```
❌ Błąd Google Calendar credentials not available
```

**Rozwiązanie**: Wykonaj ponownie `python cli.py register`

### Problemy z połączeniem

```bash
# Sprawdź status kontenerów
docker-compose ps

# Restart systemu
docker-compose down
docker-compose up -d
```

### Błędy walidacji JSON

- Sprawdź format plików `schedule.json` i `timetable.json`
- Porównaj ze schematami w `processor/app/planvalidation/`

## 🤝 Kontakt

- **Repozytorium**: https://github.com/hallu-boss/AutoCal
- **Dokumentacja**: Zobacz `pkims_dokumentacja_245817.pdf`
- **Credentials**: Skontaktuj się z właścicielem projektu

## 📄 Licencja

Projekt edukacyjny - praca inżynierska

---

⚠️ **Pamiętaj**: Bez pliku `credentials.json` od właściciela projektu system nie będzie działał prawidłowo!
