# Rezultati evaluacije

Automatski generisano pokretanjem `python -m evaluation.run_evaluation`. Svi brojevi su reproduktivni (fiksirani random seed-ovi).

## 1. Performanse ZKP (Schnorr) protokola

Prosek od 1000 mernih ciklusa po operaciji, na 2048-bitnoj grupi:

| Operacija | Prosek (ms) | Min (ms) | Max (ms) |
|---|---|---|---|
| Generisanje kljuceva | 23.540 | 22.853 | 30.810 |
| Commitment | 23.509 | 22.874 | 30.602 |
| Response | 0.002 | 0.001 | 0.010 |
| Verifikacija | 24.022 | 23.443 | 29.349 |

## 2. Stopa laznih pozitiva (normalan saobracaj)

Model testiran na ODVOJENOM test skupu (drugaciji random seed od treninga, da se izbegne data leakage):

| Senzor | Lazni pozitivi | Ukupno ocitavanja | Stopa |
|---|---|---|---|
| temperature | 11 | 500 | 2.20% |
| humidity | 4 | 500 | 0.80% |

## 3. Osetljivost detekcije napada (true positive rate)

Po 50 pokusaja za svaku velicinu naglog skoka u odnosu na stabilnu prethodnu vrednost:

### Osetljivost detekcije — temperature

| Velicina naglog skoka | Stopa detekcije |
|---|---|
| ±1 | 82% |
| ±2 | 100% |
| ±4 | 100% |
| ±8 | 100% |
| ±16 | 100% |
| ±32 | 100% |

### Osetljivost detekcije — humidity

| Velicina naglog skoka | Stopa detekcije |
|---|---|
| ±1 | 78% |
| ±2 | 100% |
| ±4 | 100% |
| ±8 | 100% |
| ±16 | 100% |
| ±32 | 100% |

## 4. Otpornost na spoofing napad

Od 100 pokusaja autentikacije sa nasumicnim (pogresnim) privatnim kljucem, gateway je odbio 100/100 (100.0%).

## 5. Napomena o replay i brute-force napadima

Otpornost na replay i brute-force napade je dokazana kroz automatizovane integracione testove (`tests/test_gateway_attacks.py`), ne kroz statisticko merenje, jer je ishod deterministican (matematicki garantovan svezinom challenge-a, odnosno pragom za detekciju). Pokreni `pytest tests/ -v` za potvrdu da svi testovi prolaze.
