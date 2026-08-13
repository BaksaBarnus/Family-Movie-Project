# Family Movie Catalog & Wishlist

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)

> Interaktív filmkatalógus és kívánságlista az otthoni hálózati médiaszerverhez.

![App Screenshot](https://i.imgur.com/IJYuemQ.jpeg)

# Projekt célja

Az otthoni hálózaton futó médiaszerveren elérhető filmek és sorozatok listázása egy interaktív weboldalon, ahol akár kívánságokat is be lehet küldeni. Ez megkönnyíti a családi filmezést olyan módon, hogy bárkinek kívánsága lenne egy új tételre, azt egyszerűen felviheti az adatbázisba a weboldalon keresztül, innen pedig az üzemeltető tudni fogja mit kell hozzáadnia a meglévő állományhoz. Emellett, ha nincs konkrét elképzelés, a meglévők közül is szabadon választhatnak, döntésüket pedig a megjelenő borítóképek, leírások és értékelések segítik.

## Megvalósítás
    •	Full-Stack fejlesztés: Tartalmazza a felhasználói felületet (frontend), a szerveroldali logikát (backend) és az adatbázis-architektúrát.
    •	Külső API integráció: Harmadik féltől származó API (TMDB API) segíti a filmek / sorozatok valós idejű adatai - pl.: név, megjelenési év, borítókép, értékelés – lekéréseit.
    •	Adatmodell: Relációs adatbázis (PostgreSQL) tárolja a médiaelemek adatait, illetve a kívánságokét is.

## Meglévő architektúra
    Egy Linux alapú, nyílt forráskódú operációs rendszert futtató router, amelyben egy külső meghajtó szolgáltatja a médiafájlokat a fent említett médiaszervernek. Erre a meghajtóra van elmentve a médiaszerver saját adatbázisa. Emellett egy fájlszerver biztosítja a meghajtó távoli elérését.
 
# Technikai dokumentáció

## Tech-Stack
    •	Frontend: HTML5, CSS3 / JavaScript
    •	Backend: Python
    •	Adatbázis: PostgreSQL
    •	Külső API: TMDB (The Movie Database) API
    •	DevOps & Eszközök: Git, GitHub, Docker

## Rendszerarchitektúra
    •	Filmadatbázis & Keresés
        -	Filmkeresés cím alapján
        -	Részletes adatlap megjelenítése (borítókép, leírás, értékelés)
    •	Interaktív funkció
        -	Kívánság beküldése az állomány bővítésére

## Megoldások

## Adattranszformáció

A médiaszerver (miniDLNA) saját adatbázisához SQLite3-at használ. Ebből transzformáljuk át az adatokat a saját PostgreSQL adatbázisba.

    •	Temporálisan lemásolja a meglévő adatbázis egészét, elkerülve az esetleges adatütközéseket.

    •	A médiaelemek fájlneve sokszor tartalmaz rövidítéseket, illetve egyéb technikai adatot, így a szülőmappa nevéből nyeri ki a nyers címet. Ezt egy ’regex’ segítségével formázza a TMDB-ben kereshető formátumúvá.

    •	Kezeli a magyar ékezetes karaktereket.

    •	Kiszűri a megadott méret alatti fájlokat.

    •	A megtisztított címet adja át a TMDB API-nak, a visszakapott adatokat tölti fel a PostgrSQL adatbázisba.

## Megjelenítés

    •   A könnyebb átláthatóság jegyében az alkalmazás megjeleníti a film magyar, illetve angol nevét is. 

    •   Szintén megjelenik a műfaj, évszám, értékelés és egy rövid összefoglaló, amit a külső API-n keresztül kap meg az adatbázis.

    •   Megjeleníti a médiaelemek számát, illetve előre-hátra lehet lapozni ezeket kártyás formában.

## Keresés

    •   A keresés a gépeléssel egyidejűleg történik, mindig az első legpontosabb egyezést adja vissza

    •   Használható az angol, illetve magyar cím is

## Kívánságlista

    •   Egy leegyszerűsített lista, amelybe fel lehet vinni tetszőleges szöveget, illetve ki is lehet törölni

    •   Egyelőre az alkalmazás ezen része nyitott a további fejlesztésre, akár felhasználókezeléssel megvalósított használat, 
    a prioritás figyelembe vétele, vagy konkrét keresés és kiválasztás az API-n keresztül.

## Valós idejű szinkronizáció

    •   Az alkalmazás figyelembe veszi a beállított meghajtón történő változásokat, ilyenkor szinkronizálja azt az adatbázissal.
    
## Konténerizáció

    •   Egy docker konténerbe csomagolva az egész "plug & play", csak magát a médiaszerver saját adatbázis útvonalát kell átírni.

## API Végpontok

    | Metódus       | Végpont               | Leírás                           |
    | ------------- |:---------------------:| --------------------------------:|
    | GET           |  /api/movies          | Filmek listázása                 |
    | GET           |  /api/wishlist        |   Jelenlegi kívánságok lekérésa  |
    | POST          |  /api/wishlist        |    Új kívánság hozzáadása        |
    | DELETE        |  /api/wishlist?={id}  | Kívánság törlése                 |