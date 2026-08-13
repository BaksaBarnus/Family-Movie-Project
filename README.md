# Projekt célja

Az otthoni hálózaton futó médiaszerveren elérhető filmek és sorozatok listázása egy interaktív weboldalon, ahol akár kívánságokat is be lehet küldeni. Ez megkönnyíti a családi filmezést olyan módon, hogy bárkinek kívánsága lenne egy új tételre, azt egyszerűen felviheti az adatbázisba a weboldalon keresztül, innen pedig az üzemeltető tudni fogja mit kell hozzáadnia a meglévő állományhoz. Emellett, ha nincs konkrét elképzelés, a meglévők közül is szabadon választhatnak, döntésüket pedig a megjelenő borítóképek, leírások és értékelések segítik.

## Megvalósítás
    •	Full-Stack fejlesztés: Tartalmazza a felhasználói felületet (frontend), a szerveroldali logikát (backend) és az adatbázis-architektúrát.
    •	Külső API integráció: Harmadik féltől származó API (TMDB API) segíti a filmek / sorozatok valós idejű adatai - pl.: név, megjelenési év, borítókép, értékelés – lekéréseit.
    •	Adatmodell: Relációs adatbázis (PostgreSQL) tárolja a médiaelemek adatait, illetve a kívánságokét is.
    Meglévő architektúra
    Egy Linux alapú, nyílt forráskódú operációs rendszert futtató router, amelyben egy külső meghajtó szolgáltatja a médiafájlokat a fent említett médiaszervernek. Erre a meghajtóra van elmentve a médiaszerver saját adatbázisa. Emellett egy fájlszerver biztosítja a meghajtó távoli elérését.
 
# Technikai dokumentáció

# Tech-Stack
    •	Frontend: HTML5, CSS3 / JavaScript
    •	Backend: Python
    •	Adatbázis: PostgreSQL
    •	Külső API: TMDB (The Movie Database) API
    •	DevOps & Eszközök: Git, GitHub, Docker

# Rendszerarchitektúra
    •	Filmadatbázis & Keresés
        -	Filmkeresés cím alapján
        -	Részletes adatlap megjelenítése (borítókép, leírás, értékelés)
    •	Interaktív funkció
        -	Kívánság beküldése az állomány bővítésére

# Megoldások

## Adattranszformáció

A médiaszerver (miniDLNA) saját adatbázisához SQLite3-at használ. Ebből transzformáljuk át az adatokat a saját PostgreSQL adatbázisba.
    •	Temporálisan lemásolja a meglévő adatbázis egészét, elkerülve az esetleges adatütközéseket.
    •	A médiaelemek fájlneve sokszor tartalmaz rövidítéseket, illetve egyéb technikai adatot, így a szülőmappa nevéből nyeri ki a nyers címet. Ezt egy ’regex’ segítségével formázza a TMDB-ben kereshető formátumúvá.
    •	Kezeli a magyar ékezetes karaktereket
    •	Kiszűri a megadott méret alatti fájlokat
    •	A megtisztított címet adja át a TMDB API-nak, a visszakapott adatokat tölti fel a PostgrSQL adatbázisba.
