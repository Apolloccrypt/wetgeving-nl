---
title: "Regeling van de Staatssecretaris van Infrastructuur en Waterstaat, van 3 juni 2025, nr. IENW/BSK-2025/130201, houdende regels met betrekking tot de centrale database taxivervoer (Regeling centrale database taxivervoer) [KetenID WGK026754]"
citeertitel: "Regeling centrale database taxivervoer"
identifier: "BWBR0051129"
categorie: "Milieu"
soort: "ministeriele-regeling"
publicatiedatum: 2025-07-01
laatste_update: 2025-07-01
status: geldig
toestand: 2025-07-01
bron: "https://wetten.overheid.nl/BWBR0051129"
opgehaald: 2026-09-08
---

# Regeling van de Staatssecretaris van Infrastructuur en Waterstaat, van 3 juni 2025, nr. IENW/BSK-2025/130201, houdende regels met betrekking tot de centrale database taxivervoer (Regeling centrale database taxivervoer) [KetenID WGK026754]

#### § 1. Begripsbepalingen

##### Artikel 1

In deze regeling wordt verstaan onder:

- *Besluit:*
 [Besluit personenvervoer 2000](https://wetten.overheid.nl/jci1.3:c:BWBR0011982);

- *centrale applicatie:* applicatie die taxivervoergegevens ontvangt van een of meerdere registratiemiddelen en deze aanlevert aan de CDT via de CDT meldingen API;

- *CDT:* centrale database taxivervoer;

- *CDT Meldingen API:* voorziening voor het uitwisselen van taxivervoergegevens tussen een centrale applicatie en de CDT;

- *gebeurtenis:* voorval dat plaatsvindt binnen het registratiemiddel, zijnde een melding, fout of storing;

- *ICT-oplossing:* het geheel aan digitale technieken en processen voor het registreren van taxivervoergegevens en het aanleveren van deze gegevens aan de CDT;

- *pauze:* een periode van tenminste 15 achtereenvolgende minuten waarin de bestuurder geen werkzaamheden verricht en vrijelijk over zijn tijd kan beschikken;

- *taxivervoergegevens:* gegevens als bedoeld in [artikel 83b, tweede lid, van het Besluit](https://wetten.overheid.nl/jci1.3:c:BWBR0011982&artikel=83b);

- *twee factor authenticatie:* methode waarbij de identiteit van een persoon wordt vastgesteld op basis van twee verschillende factoren.

#### § 2. Registratie en aanlevering van taxivervoergegevens

##### Artikel 2. (Registreren en aanleveren van taxivervoergegevens)

1. De centrale applicatie waarvan de vervoerder gebruik maakt, wordt aangesloten op de CDT als het registratiemiddel en de centrale applicatie voldoen aan de in deze regeling opgenomen voorwaarden.

2. Via de CDT Meldingen API meldt de vervoerder van welke ICT-oplossing gebruik wordt gemaakt.

3. De bestuurder maakt gebruik van het registratiemiddel, dat ter beschikking is gesteld door de vervoerder, om taxivervoergegevens te registreren.

4. De taxivervoergegevens worden door het registratiemiddel geregistreerd en via de centrale applicatie realtime aangeleverd aan de CDT Meldingen API, tenzij sprake is van omstandigheden ten gevolge waarvan deze gegevens niet realtime kunnen worden geregistreerd of aangeleverd.

5. De omstandigheden waaronder taxivervoergegevens niet realtime kunnen worden aangeleverd, bedoeld in het vijfde lid, zijn beperkt tot:

- a. het niet beschikbaar zijn van de CDT Meldingen API als gevolg van technische problemen of onderhoud;

- b. een verstoring van de gegevensoverdracht tussen centrale applicatie en CDT Meldingen API.

6. De niet tijdig aangeleverde taxivervoergegevens, bedoeld in het vierde lid, worden onverwijld aangeleverd aan de CDT Meldingen API zodra de omstandigheden, bedoeld in het vijfde lid, zich niet meer voordoen.

7. Het registreren en aanleveren van taxivervoergegevens vindt plaats aan de hand van de beschrijving, bedoeld in de [bijlage](https://wetten.overheid.nl/BWBR0051129).

##### Artikel 3. (Zorgplichten vervoerder)

1. De vervoerder stelt aan de bestuurder een deugdelijk registratiemiddel ter beschikking.

2. De vervoerder draagt er zorg voor dat de bestuurder een registratie bijhoudt van de gegevens als genoemd in [artikel 83b, tweede lid, van het Besluit](https://wetten.overheid.nl/jci1.3:c:BWBR0011982&artikel=83b).

3. Indien het registratiemiddel ondeugdelijk, defect of verloren gegaan is, zorgt de vervoerder binnen drie werkdagen voor herstel of een vervangend registratiemiddel.

4. De vervoerder draagt er zorg voor dat de gegevens, als bedoeld in [artikel 7, zesde lid](https://wetten.overheid.nl/jci1.3:c:BWBR0051129&paragraaf=2&artikel=7&z=2025-07-01&g=2025-07-01), onverwijld en waarheidsgetrouw worden aangeleverd aan de CDT Meldingen API.

5. De vervoerder draagt er zorg voor dat de aanlevering aan de CDT Meldingen API zonder foutmeldingen en waarschuwingsberichten verloopt.

6. Als foutmeldingen of waarschuwingsberichten worden ontvangen, verhelpt de vervoerder onverwijld de oorzaken ervan.

##### Artikel 4. (Validatie van de bestuurder)

1. De vervoerder valideert de gegevens van de bestuurder bij de CDT Meldingen API voordat de bestuurder voor de eerste keer met het registratiemiddel taxivervoer verricht voor de vervoerder.

2. Validatie vindt plaats door het aanleveren van het chauffeursnummer en de rijbewijsgegevens van de bestuurder zoals omschreven in de [bijlage](https://wetten.overheid.nl/BWBR0051129).

3. De bestuurder is gevalideerd als:

- a. de rijbewijsgegevens van een geldig rijbewijs zijn;

- b. het chauffeursnummer van een geldige bevoegdheid taxivervoer is; en

- c. het chauffeursnummer en het rijbewijs van dezelfde persoon zijn.

4. Een niet-gevalideerde bestuurder mag geen taxivervoer voor een vervoerder verrichten, tenzij de CDT Meldingen API niet beschikbaar is ten tijde van de validatiepoging.

5. Als sprake is van een situatie als bedoeld in het vierde lid, valideert de vervoerder de gegevens als bedoeld in het tweede lid, onverwijld, zodra de CDT Meldingen API weer beschikbaar is.

6. Als de bestuurder niet in het bezit is van een Nederlands rijbewijs, maar van een niet-Nederlands rijbewijs, valideert de vervoerder het chauffeursnummer van de bestuurder.

7. De bestuurder met een niet-Nederlands rijbewijs is gevalideerd als het chauffeursnummer van een geldige bevoegdheid taxivervoer is.

##### Artikel 5. (Validatie van de auto waarmee taxivervoer wordt verricht)

1. De vervoerder valideert een auto waarmee taxivervoer wordt verricht voordat deze voor de eerste keer voor de vervoerder met het registratiesysteem van de CDT wordt gebruikt en legt dit vast.

2. Validatie vindt plaats door het elektronisch valideren van het kentekenbewijs.

3. In een niet door de vervoerder gevalideerde auto waarmee taxivervoer wordt verricht, wordt door een bestuurder geen taxivervoer verricht.

##### Artikel 6. (Aanmelden van de bestuurder)

1. Bij aanvang van de werkzaamheden aan boord van een auto waarmee taxivervoer wordt verricht meldt de bestuurder zich aan op het registratiemiddel.

2. De bestuurder die in het bezit is van een Nederlands rijbewijs meldt zich aan door zijn Nederlands rijbewijs elektronisch te authentiseren op het registratiemiddel.

3. Als het Nederlands rijbewijs defect is, meldt de bestuurder zich gedurende een periode van maximaal tien aaneengesloten dagen aan door middel van twee factor authenticatie.

4. De bestuurder die niet in het bezit is van een Nederlands rijbewijs en wel in het bezit is van een niet-Nederlands rijbewijs meldt zich aan door middel van twee factor authenticatie.

5. Zonder aanmelden is het een bestuurder niet toegestaan om taxivervoer te verrichten.

##### Artikel 7. (Gebruik van het registratiemiddel door de bestuurder)

1. Indien de bestuurder, voorafgaand aan de melding, bedoeld in [artikel 6, eerste lid](https://wetten.overheid.nl/jci1.3:c:BWBR0051129&paragraaf=2&artikel=6&z=2025-07-01&g=2025-07-01), andere werkzaamheden heeft verricht na zijn laatste afmelding als bedoeld in het zevende lid van dit artikel, registreert hij de begin- en eindtijden van de andere werkzaamheden bij de melding als bedoeld in [artikel 6, eerste lid](https://wetten.overheid.nl/jci1.3:c:BWBR0051129&paragraaf=2&artikel=6&z=2025-07-01&g=2025-07-01).

2. De bestuurder meldt een rit aan op het registratiemiddel op het moment dat het vervoeren van personen aanvangt.

3. De bestuurder meldt een rit af op het registratiemiddel op het moment dat het vervoeren van personen is beëindigd.

4. Ingeval het registratiemiddel niet gekoppeld is aan de taxameter, bedoeld in [artikel 78 van het Besluit personenvervoer 2000](https://wetten.overheid.nl/jci1.3:c:BWBR0011982&artikel=78), voert de bestuurder handmatig de door de taxameter aangegeven totaalprijs in. Als voor het vervoer geen taxameter verplicht is en de volledige ritprijs direct na de rit wordt voldaan voert de bestuurder de door de reiziger verschuldigde vergoeding in.

5. Gedurende de periode dat er geen registratiemiddel beschikbaar is, als genoemd in [artikel 3, derde lid](https://wetten.overheid.nl/jci1.3:c:BWBR0051129&paragraaf=2&artikel=3&z=2025-07-01&g=2025-07-01), registreert de bestuurder zijn taxivervoersgegevens op een andere inzichtelijke en controleerbare wijze.

6. De bestuurder levert de registratie, genoemd in het vijfde lid, uiterlijk de derde werkdag als bedoeld in [artikel 3, derde lid](https://wetten.overheid.nl/jci1.3:c:BWBR0051129&paragraaf=2&artikel=3&z=2025-07-01&g=2025-07-01), aan bij de vervoerder.

7. Bij beëindiging van de werkzaamheden aan boord van een auto waarmee taxivervoer wordt verricht meldt de bestuurder zich af op het registratiemiddel.

8. De bestuurder meldt op het moment dat deze plaats vinden op het registratiemiddel het begin en einde van pauzes die hij tijdens zijn werkzaamheden aan boord van een auto waarmee taxivervoer wordt verricht geniet.

#### § 3. Techniek

##### Artikel 8. (Registratiemiddel)

1. Het registratiemiddel bevat of heeft de volgende eigenschappen:

- a. een bewegingsdetectie van het registratiemiddel;

- b. een locatiebepaling met een nauwkeurigheid van ten minste 25 meter;

- c. de functionaliteit om de laatst bekende locatie vast te houden;

- d. de functionaliteit om op basis van de locatiebepaling een afgelegde afstand te bepalen met een maximale afwijking van 15%;

- e. een tijdsbepaling met een nauwkeurigheid van ten minste 1 seconde en synchronisatie met een geijkte externe tijdfunctie;

- f. voorzieningen om de bestuurder te authentiseren als genoemd in [artikel 6](https://wetten.overheid.nl/jci1.3:c:BWBR0051129&paragraaf=2&artikel=6&z=2025-07-01&g=2025-07-01);

- g. de functionaliteit om unieke identificatiecodes van diensten, ritten, pauzes en gebeurtenissen te genereren;

- h. de functionaliteit om diensten, verrichtingen en andere werkzaamheden als genoemd in [artikel 83b, tweede lid, onderdeel l van het Besluit](https://wetten.overheid.nl/jci1.3:c:BWBR0011982&artikel=83b), aan en af te melden via de centrale applicatie;

- i. voorzieningen die taxivervoergegevens realtime doorsturen naar de centrale applicatie;

- j. voorzieningen die ervoor zorgen dat er geen taxivervoergegevens verloren kunnen gaan;

- k. de functionaliteit voor de bestuurder om alleen auto's te kunnen opgeven die de vervoerder voor hem heeft toegestaan;

- l. de functionaliteit voor de bestuurder om zich aan te kunnen melden voor vervoerders die hem dat toestaan.

2. Het is niet toegestaan het registratiemiddel op een wijze te gebruiken die maakt dat taxivervoergegevens kunnen worden gewijzigd of verwijderd voordat deze zijn aangeleverd in de CDT.

##### Artikel 9. (Centrale applicatie)

1. Het aanleveren van taxivervoergegevens vanaf het registratiemiddel aan de CDT vindt plaats via een centrale applicatie.

2. De centrale applicatie bevat of heeft de volgende eigenschappen:

- a. een functionaliteit om alle ontvangen gegevens direct en ongewijzigd door te sturen naar de CDT Meldingen API;

- b. een functionaliteit die ervoor zorgt dat berichten in chronologische volgorde van registratie tijdens de werkzaamheden aan boord van de auto waarmee taxivervoer wordt verricht worden aangeboden aan de CDT Meldingen API;

- c. een functionaliteit die maakt dat een volgend bericht aan de CDT Meldingen API pas wordt aangeboden als het voorgaande bericht succesvol is verwerkt.

##### Artikel 10. (Informatiebeveiliging)

1. De vervoerder maakt gebruik van een ICT-oplossing en een organisatie die zijn gecertificeerd voor ISO 27001. De certificatie wordt verricht door een certificerende instelling die is geaccrediteerd door de Raad voor Accreditatie of een andere accreditatie instelling die is erkend in een lidstaat van de Europese Unie.

2. De certificering, bedoeld in het eerste lid, heeft als werkingsgebied alle functionaliteit die gegevens levert aan de CDT Meldingen API. De functionaliteit omvat ten minste alle registratiemiddelen en de centrale applicatie.

#### § 4. Overgangs- en slotbepalingen

##### Artikel 11. (Inwerkingtreding)

Deze regeling treedt in werking met ingang van 1 juli 2025.

##### Artikel 12. (Citeertitel)

Deze regeling wordt aangehaald als: Regeling centrale database taxivervoer.
