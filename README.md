# Smart Home Security Platform

Simulacija IoT mreže pametnog doma sa autentikacijom uređaja zasnovanom na **Zero-Knowledge Proof (Schnorr)** protokolu, anomaly detection sistemom i live dashboard-om. Diplomski rad iz predmeta *Internet of Things*.

## Zašto ovaj projekat

Klasična IoT autentikacija (lozinke, statički API ključevi) zahteva da uređaj otkrije svoju tajnu pri svakoj konekciji, što je rizično u slučaju presretanja saobraćaja. Ovaj projekat implementira **Schnorr zero-knowledge proof** protokol — uređaj dokazuje da poseduje privatni ključ bez da ga ikada pošalje preko mreže.

## Arhitektura

```
IoT uređaj (prover) --ZKP challenge/response--> Auth gateway (verifier)
                                                        |
                                                  izdaje token
                                                        v
                                                  MQTT broker (Mosquitto)
                                                        |
                                                        v
                                              Anomaly detection (ML)
                                                        |
                                                        v
                                                   Dashboard (live)
```

## Status / roadmap

- [x] **Faza 1** — Mosquitto broker + simulirani IoT uređaji koji publish-uju senzorske podatke
- [ ] **Faza 2** — ZKP (Schnorr) autentikacija uređaja preko auth gateway-a
- [ ] **Faza 3** — Anomaly detection (sumnjivi podaci + neuspeli auth pokušaji)
- [ ] **Faza 4** — Live dashboard
- [ ] **Faza 5** — Testiranje napada (spoofing, replay, DoS) i evaluacija

## Tehnologije

| Komponenta | Tehnologija |
|---|---|
| Simulirani uređaji | Python, `paho-mqtt` |
| ZKP autentikacija | Python, Schnorr protokol (implementacija od nule) |
| Auth gateway | FastAPI, SQLite |
| MQTT broker | Eclipse Mosquitto |
| Anomaly detection | scikit-learn (Isolation Forest) |
| Dashboard | Flask + Chart.js |
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
python devices/device_simulator.py --device-id sensor-temp-01 --sensor-type temperature
python devices/device_simulator.py --device-id sensor-hum-01 --sensor-type humidity
python devices/device_simulator.py --device-id sensor-motion-01 --sensor-type motion
```

Provera da li poruke stižu (ako imaš `mosquitto-clients`):

```bash
mosquitto_sub -h localhost -t "home/+/+" -v
```

## Struktura projekta

```
smart-home-security-platform/
├── devices/         # simulacija IoT uređaja
├── gateway/         # ZKP auth gateway (faza 2)
├── broker/          # Mosquitto konfiguracija
├── dashboard/       # live dashboard (faza 4)
├── docs/            # dokumentacija, dijagrami, beleške za diplomski
├── docker-compose.yml
└── requirements.txt
```

## Literatura (ZKP za IoT autentikaciju)

- *Lightweight zero-knowledge authentication scheme for IoT embedded devices (LZIA)*
- *TinyZKP: Non-interactive zero knowledge proofs for IoT device authentication*
- *BANZKP: lightweight authentication scheme for body area networks*
- *SEAS: Secure and Efficient Authentication Scheme for Large-Scale IoT Devices Based on Zero-Knowledge Proof*
