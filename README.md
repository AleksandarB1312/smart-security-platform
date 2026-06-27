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
- [x] **Faza 5** — Testiranje napada (spoofing, replay, DoS) i evaluacija

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

## Pokretanje (Faza 5 — Testiranje napada i evaluacija)

Formalni, automatizovani testovi napada (spoofing, replay, brute-force) — koriste FastAPI TestClient, ne treba im pokrenut gateway ni broker:

```bash
pytest tests/test_gateway_attacks.py -v
```

Pokreni kompletnu evaluaciju (ZKP performanse, stopa lažnih pozitiva, osetljivost detekcije po veličini napada, otpornost na spoofing) — generiše `docs/rezultati_evaluacije.md` sa stvarnim, reproduktivnim brojevima za poglavlje "Rezultati":

```bash
python -m evaluation.run_evaluation
```

**Šta se tačno testira:**

| Napad | Kako se testira | Gde |
|---|---|---|
| Spoofing (lažan privatni ključ) | 100 pokušaja sa nasumičnim ključem | `evaluation/run_evaluation.py` + `tests/test_gateway_attacks.py` |
| Replay (presretnut odgovor) | Ponovno slanje starog response-a na nov challenge | `tests/test_gateway_attacks.py` |
| Brute-force (više pokušaja zaredom) | 4+ neuspela pokušaja, provera da se loguju | `tests/test_gateway_attacks.py` |
| Nonce reuse (loša implementacija) | Dokaz da se privatni ključ matematički izvlači | `tests/test_schnorr.py` |
| Anomalni senzorski podaci | Skokovi različitih veličina (±1 do ±32) | `evaluation/run_evaluation.py` |

**Napomena o metodologiji:** stopa lažnih pozitiva se mери na ODVOJENOM test skupu (drugačiji random seed od trening skupa) — bitno da se izbegne data leakage (testiranje modela na podacima koje je već "vidiо").

## Poznata ograničenja i budući rad

Iskreno dokumentovano (korisno za poglavlje "Ograničenja i budući rad" u diplomskom):

- **Mosquitto broker ne validira token na transportnom nivou** (Faza 2.5, namerno preskočena) — gateway izdaje token samo nakon uspešnog ZKP dokaza, ali sam MQTT broker trenutno prima konekciju od bilo kog klijenta (`allow_anonymous true`). Anomaly detection sloj delimično nadoknađuje ovo (vidi tačku 4 evaluacije), ali prava "defense in depth" arhitektura bi zahtevala da i broker sam proверava token (npr. preko `password_file` ili dynamic security plugin-a).
- **Sinhrona priroda ZKP autentikacije** — trenutni protokol je interaktivan (challenge/response u 2 HTTP poziva); produkcioni sistem bi mogao koristiti non-interactive varijantu (Fiat-Shamir heuristika) za manji network overhead.
- **Token revokacija** — izdati JWT tokeni važe do isteka (5 min) bez mehanizma za prevremeno opozivanje (npr. ako se uređaj kasnije otkrije kao kompromitovan).
- **Anomaly detection feature set** — koristi samo (vrednost, devijacija od rolling proseka); bogatiji feature set (sezonalnost, korelacija između senzora) bi mogao dalje smanjiti stopu lažnih pozitiva.

## Struktura projekta

```
smart-home-security-platform/
├── crypto/          # Schnorr ZKP protokol (deli ga gateway i uređaji)
├── devices/         # simulacija IoT uređaja, ZKP klijent, deljena sensors.py logika
├── gateway/         # auth gateway (FastAPI) + registar uređaja + auth_failures log (SQLite)
├── anomaly/         # Isolation Forest modeli, live monitor, attack simulator
├── dashboard/       # Flask live dashboard (MQTT listener + JSON API + frontend)
├── evaluation/      # evaluacija performansi i bezbednosti (Faza 5)
├── broker/          # Mosquitto konfiguracija
├── tests/           # testovi kriptografije, anomaly detection i napada na gateway
├── docs/            # dokumentacija, dijagrami, rezultati_evaluacije.md
├── docker-compose.yml
└── requirements.txt
```

## Literatura (ZKP za IoT autentikaciju)

- *Lightweight zero-knowledge authentication scheme for IoT embedded devices (LZIA)*
- *TinyZKP: Non-interactive zero knowledge proofs for IoT device authentication*
- *BANZKP: lightweight authentication scheme for body area networks*
- *SEAS: Secure and Efficient Authentication Scheme for Large-Scale IoT Devices Based on Zero-Knowledge Proof*
