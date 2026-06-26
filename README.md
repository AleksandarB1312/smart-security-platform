# Smart Home Security Platform

Simulacija IoT mreže pametnog doma sa autentikacijom uređaja zasnovanom na **Zero-Knowledge Proof (Schnorr)** protokolu, anomaly detection sistemom i live dashboard-om. Diplomski rad iz predmeta *Internet of Things*.

## Zašto ovaj projekat

Klasična IoT autentikacija (lozinke, statički API ključevi) zahteva da uređaj otkrije svoju tajnu pri svakoj konekciji, što je rizično u slučaju presretanja saobraćaja. Ovaj projekat implementira **Schnorr zero-knowledge proof** protokol — uređaj dokazuje da poseduje privatni ključ bez da ga ikada pošalje preko mreže.

## Arhitektura

```
IoT uređaj (prover) --ZKP challenge/response--> Auth gateway (verifier)
                                                        |        |
                                                  izdaje token    neuspeli pokusaj -> auth_failures log
                                                        v
                                                  MQTT broker (Mosquitto)
                                                        |
                                                        v
                                          Anomaly detection (Isolation Forest)
                                                        |
                                                        v
                                                   Dashboard (live)
```

## Status / roadmap

- [x] **Faza 1** — Mosquitto broker + simulirani IoT uređaji koji publish-uju senzorske podatke
- [x] **Faza 2** — ZKP (Schnorr) autentikacija uređaja preko auth gateway-a
- [ ] **Faza 2.5** — Mosquitto sam validira token (trenutno gateway izdaje token, ali broker ga još ne proverava)
- [x] **Faza 3** — Anomaly detection (sumnjivi podaci + neuspeli auth pokušaji)
- [x] **Faza 4** — Live dashboard
- [ ] **Faza 5** — Testiranje napada (spoofing, replay, DoS) i evaluacija

## Tehnologije

| Komponenta | Tehnologija |
|---|---|
| Simulirani uređaji | Python, `paho-mqtt` |
| ZKP autentikacija | Python, Schnorr protokol (implementacija od nule) |
| Auth gateway | FastAPI, SQLite |
| MQTT broker | Eclipse Mosquitto |
| Anomaly detection | scikit-learn (Isolation Forest) |
| Dashboard | Flask, vanilla JS + inline SVG (bez eksternih CDN zavisnosti) |
| Infrastruktura | Docker Compose |

## Pokretanje (Faza 1)

Pokreni broker:

```bash
docker compose up -d
```

Instaliraj zavisnosti:

```bash
pip install -r requirements.txt
```

Pokreni jedan ili više simuliranih uređaja (svaki u svom terminalu):

```bash
python -m devices.device_simulator --device-id sensor-temp-01 --sensor-type temperature
python -m devices.device_simulator --device-id sensor-hum-01 --sensor-type humidity
python -m devices.device_simulator --device-id sensor-motion-01 --sensor-type motion
```

**Napomena:** sve komande u ovom projektu se pokreću sa `-m` oznakom iz root foldera (npr. `python -m devices.device_simulator`, ne `python devices/device_simulator.py`) — to je neophodno zbog deljenih paketa (`crypto`, `devices`, `gateway`, `anomaly`) koji se međusobno importuju.

Provera da li poruke stižu (ako imaš `mosquitto-clients`):

```bash
mosquitto_sub -h localhost -t "home/+/+" -v
```

## Pokretanje (Faza 2 — ZKP autentikacija)

Pokreni auth gateway (u zasebnom terminalu, ostavi da radi):

```bash
uvicorn gateway.main:app --reload --port 8000
```

Registruj uređaj (generiše par ključeva, javni ključ šalje gateway-u, privatni čuva lokalno u `devices/keys/`):

```bash
python -m devices.register_device --device-id sensor-temp-01
```

Pokreni "sigurnu" verziju simulatora — prvo se ZKP autentikuje, pa tek onda publish-uje na MQTT:

```bash
python -m devices.secure_device_simulator --device-id sensor-temp-01 --sensor-type temperature
```

**Napomena:** sve komande iz Faze 2 pokreći iz root foldera projekta (zbog `-m` oznake koja koristi Python pakete `crypto`, `gateway`, `devices`).

Pokreni testove kriptografskog modula (uključujući dokaz da ponovljen nonce otkriva privatni ključ):

```bash
pytest tests/ -v
```

Swagger dokumentacija gateway-a (lepo za demonstraciju na odbrani): `http://localhost:8000/docs`

Lista nedavnih neuspelih auth pokušaja (brute-force log): `http://localhost:8000/security/failed-attempts`

## Pokretanje (Faza 3 — Anomaly Detection)

Istrenirај modele (Isolation Forest, po jedan za temperaturu i vlažnost — `motion` je binaran i ne koristi ovaj pristup):

```bash
python -m anomaly.train_model
```

Pokreni live monitor (sluša sve `home/+/+` MQTT poruke, u zasebnom terminalu):

```bash
python -m anomaly.live_monitor
```

U drugom terminalu, pokreni normalan saobraćaj (npr. Faza 1 ili Faza 2 simulator) — monitor treba da ispisuje `[OK]` za svaku poruku. Zatim simuliraj napad/kvar uređaja:

```bash
python -m anomaly.attack_simulator --device-id sensor-temp-01 --sensor-type temperature --value 85.0
```

Monitor treba da ispiše `[ANOMALIJA]` i objavi upozorenje na MQTT temu `alerts/<device_id>/<sensor_type>`.

**Kako detekcija radi:** model ne gleda samo da li je vrednost u dozvoljenom opsegu — koristi i **devijaciju od rolling proseka** poslednjih 5 očitavanja tog uređaja. Zato hvata i suptilne anomalije (npr. nagli skok sa 22°C na 26°C — tehnički "u opsegu", ali nerealno brza promena), ne samo apsurdne vrednosti. Ovo je dokumentovano i testirano u `tests/test_anomaly.py`.

**Bitna napomena o metodologiji:** model za "normalno" ponašanje trenira se na sintetičkim podacima generisanim istom `devices/sensors.py` logikom (random walk) koju koriste i sami simulatori uređaja — ovo je svesna odluka da bi distribucija trening podataka odgovarala stvarnom radu sistema (čest izvor problema u ML sistemima, poznat kao *train/serve skew* — vredna napomena za poglavlje o metodologiji u radu).

Pokreni testove za kriptografiju i anomaly detection zajedno:

```bash
pytest tests/ -v
```

## Pokretanje (Faza 4 — Live Dashboard)

Uz već pokrenut broker (i opcionalno gateway/monitor za pune podatke), pokreni dashboard u zasebnom terminalu:

```bash
python -m dashboard.app
```

Otvori u browseru: `http://localhost:5000`

Dashboard prikazuje:
- **Live kartice po uređaju** — trenutna vrednost + sparkline (poslednji 30 očitavanja), osvežava se svake 1.5s
- **Anomalije** — feed upozorenja sa `alerts/+/+` MQTT teme (puni se kad `anomaly.live_monitor` radi)
- **Bezbednosni dnevnik** — neuspeli ZKP auth pokušaji, povučeno direktno sa gateway-a (`/security/failed-attempts`)

**Napomena o tehničkom izboru:** README je ranije predviđao Chart.js za grafove, ali sam umesto toga implementirao sparkline-ove direktno u SVG-u preko vanilla JS-a — dashboard je potpuno samostalan (radi i bez interneta, nema CDN zavisnosti), što je dobra osobina za bezbednosni alat. Ako želiš bogatije grafove kasnije, Chart.js se lako dodaje.

Za potpunu demonstraciju uživo, pokreni paralelno (svaki u svom terminalu): broker, gateway, `anomaly.live_monitor`, `dashboard.app`, i jedan ili više simulatora uređaja — sve se vidi na jednom ekranu, idealno za odbranu.

## Struktura projekta

```
smart-home-security-platform/
├── crypto/          # Schnorr ZKP protokol (deli ga gateway i uređaji)
├── devices/         # simulacija IoT uređaja, ZKP klijent, deljena sensors.py logika
├── gateway/         # auth gateway (FastAPI) + registar uređaja + auth_failures log (SQLite)
├── anomaly/         # Isolation Forest modeli, live monitor, attack simulator
├── dashboard/       # Flask live dashboard (MQTT listener + JSON API + frontend)
├── broker/          # Mosquitto konfiguracija
├── tests/           # testovi kriptografskog i anomaly detection modula
├── docs/            # dokumentacija, dijagrami, beleške za diplomski
├── docker-compose.yml
└── requirements.txt
```

## Literatura (ZKP za IoT autentikaciju)

- *Lightweight zero-knowledge authentication scheme for IoT embedded devices (LZIA)*
- *TinyZKP: Non-interactive zero knowledge proofs for IoT device authentication*
- *BANZKP: lightweight authentication scheme for body area networks*
- *SEAS: Secure and Efficient Authentication Scheme for Large-Scale IoT Devices Based on Zero-Knowledge Proof*
