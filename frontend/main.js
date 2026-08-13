// ==========================================================================
// 1. GLOBÁLIS ÁLLAPOT ÉS KONSTANSOK
// ==========================================================================
let allMovies = [];
let filteredMovies = [];
let currentIndex = 0;

// TMDB Képek hivatalos hálózati elérési útjai
const TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w500';
const TMDB_BACKDROP_BASE = 'https://image.tmdb.org/t/p/w1280';

// ==========================================================================
// 2. DOM ELEMEK BEGYŰJTÉSE
// ==========================================================================
const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search');
const movieCountEl = document.getElementById('movie-count');

const posterImg = document.getElementById('poster-img');
const posterPlaceholder = document.getElementById('poster-placeholder');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const counterIndicator = document.getElementById('counter-indicator');

const movieTitle = document.getElementById('movie-title');
const movieYear = document.getElementById('movie-year');
const movieRating = document.getElementById('movie-rating');
const movieOverview = document.getElementById('movie-overview');
const movieGenres = document.getElementById('movie-genres');
const moviePath = document.getElementById('movie-path');
const bgBackdrop = document.getElementById('bg-backdrop');

// ==========================================================================
// 3. ADATOK LEKÉRÉSE A BACKENDRŐL
// ==========================================================================
async function fetchMovies() {
    try {
        const response = await fetch('/api/movies');
        if (!response.ok) throw new Error(`HTTP hiba! Státusz: ${response.status}`);

        allMovies = await response.json();
        filteredMovies = [...allMovies];

        // Összes elem számának frissítése a fejlécben
        movieCountEl.textContent = allMovies.length;

        if (filteredMovies.length > 0) {
            renderCurrentMovie();
        } else {
            renderEmptyState("Még nincsenek filmek az adatbázisban.");
        }
    } catch (error) {
        console.error('Hiba az adatok betöltése során:', error);
        renderEmptyState("Hiba történt az adatok betöltésekor.");
    }
}

// ==========================================================================
// 4. MEGJELENÍTÉS ÉS RENDELERÉS
// ==========================================================================
function formatPath(fullPath) {
    if (!fullPath) return '-';
    // Levágja a /mnt/sda1/ vagy /mnt/bármi/ előtagot a kezdésről
    return fullPath.replace(/^\/mnt\/[^\/]+\//i, '');
}

function renderCurrentMovie() {
    if (filteredMovies.length === 0) {
        renderEmptyState("Nincs a keresésnek megfelelő találat.");
        return;
    }

    const movie = filteredMovies[currentIndex];

    // 🟢 Hivatalos magyar cím és zárójelben az eredeti angol cím megjelenítése
    // 🟢 Hivatalos magyar cím és zárójelben az eredeti angol cím megjelenítése
    const mainTitle = movie.tmdb_title || movie.clean_title || 'Cím nélkül';

    if (movie.original_title && movie.original_title.toLowerCase() !== mainTitle.toLowerCase()) {
        movieTitle.innerHTML = `${mainTitle} <span class="original-title">(${movie.original_title})</span>`;
    } else {
        movieTitle.textContent = mainTitle;
    }

    movieYear.textContent = movie.year ? movie.year : '----';
    movieRating.textContent = movie.rating ? `⭐ ${Number(movie.rating).toFixed(1)}` : '⭐ N/A';

    // 🟢 Műfajok megjelenítése
    if (movie.genres) {
        movieGenres.textContent = movie.genres;
        movieGenres.style.display = 'inline-block';
    } else {
        movieGenres.style.display = 'none';
    }

    // 🟢 Szöveges adatok kitöltése (A DUPLIKÁLT CÍM/ÉV/RATING SOROKAT KITAKARÍTOTTUK INNEN!)
    movieOverview.textContent = movie.overview ? movie.overview : 'Ehhez a filmhez még nincs elérhető leírás a TMDB-n.';
    moviePath.textContent = formatPath(movie.path);
    moviePath.parentElement.setAttribute('title', movie.path || '');

    // Poszter kép és elmosott háttér beállítása
    if (movie.poster_path && movie.poster_path !== "null") {
        const cleanPath = movie.poster_path.startsWith('/') ? movie.poster_path : '/' + movie.poster_path;
        const fullPosterUrl = `${TMDB_POSTER_BASE}${cleanPath}`;
        const fullBackdropUrl = `${TMDB_BACKDROP_BASE}${cleanPath}`;

        // Betöltjük a képet
        posterImg.src = fullPosterUrl;

        // 🟢 HA A KÉP SIKERESEN BETÖLTŐDÖTT:
        posterImg.onload = () => {
            posterImg.classList.remove('hidden');
            posterPlaceholder.style.display = 'none';
        };

        // 🟢 HA A KÉP BETÖLTÉSE SIKERTELEN (pl. AdBlocker vagy nincs net):
        posterImg.onerror = () => {
            console.warn(`⚠️ Nem sikerült betölteni a képet: ${fullPosterUrl}`);
            posterImg.classList.add('hidden');
            posterPlaceholder.style.display = 'flex';
        };

        // Cinematic elmosott háttér
        bgBackdrop.style.backgroundImage = `url('${fullBackdropUrl}')`;
    } else {
        posterImg.classList.add('hidden');
        posterPlaceholder.style.display = 'flex';
        bgBackdrop.style.backgroundImage = 'none';
    }

    // Sorszámláló frissítése (pl. 12 / 137)
    counterIndicator.textContent = `${currentIndex + 1} / ${filteredMovies.length}`;
}

function renderEmptyState(message) {
    movieTitle.textContent = message;
    movieYear.textContent = '----';
    movieRating.textContent = '⭐ --';
    movieOverview.textContent = 'Próbálkozz más keresési kifejezéssel!';
    moviePath.textContent = '-';

    posterImg.classList.add('hidden');
    posterPlaceholder.style.display = 'flex';
    bgBackdrop.style.backgroundImage = 'none';
    counterIndicator.textContent = '0 / 0';
}

// ==========================================================================
// 5. NAVIGÁCIÓS LOGIKA
// ==========================================================================
function prevMovie() {
    if (filteredMovies.length === 0) return;
    // Körkörös lapozás visszafelé
    currentIndex = (currentIndex - 1 + filteredMovies.length) % filteredMovies.length;
    renderCurrentMovie();
}

function nextMovie() {
    if (filteredMovies.length === 0) return;
    // Körkörös lapozás előre
    currentIndex = (currentIndex + 1) % filteredMovies.length;
    renderCurrentMovie();
}

// ==========================================================================
// 6. KERESŐ LOGIKA
// ==========================================================================
function handleSearch() {
    const query = searchInput.value.trim().toLowerCase();
    clearSearchBtn.hidden = query.length === 0;

    filteredMovies = allMovies.filter(movie => {
        const cleanMatch = movie.clean_title && movie.clean_title.toLowerCase().includes(query);
        const tmdbMatch = movie.tmdb_title && movie.tmdb_title.toLowerCase().includes(query);
        const origMatch = movie.original_title && movie.original_title.toLowerCase().includes(query);
        return cleanMatch || tmdbMatch || origMatch;
    });

    currentIndex = 0;
    renderCurrentMovie();
}

function clearSearch() {
    searchInput.value = '';
    clearSearchBtn.hidden = true;
    filteredMovies = [...allMovies];
    currentIndex = 0;
    renderCurrentMovie();
    searchInput.focus();
}

// ==========================================================================
// 7. ESEMÉNYKEZELŐK (EVENT LISTENERS)
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Kezdő adatok betöltése
    fetchMovies();

    // Gombok kattintási eseményei
    prevBtn.addEventListener('click', prevMovie);
    nextBtn.addEventListener('click', nextMovie);

    // Kereső események
    searchInput.addEventListener('input', handleSearch);
    clearSearchBtn.addEventListener('click', clearSearch);

    // Billentyűzet navigáció (Bal / Jobb nyilak)
    document.addEventListener('keydown', (e) => {
        // Ha éppen a keresőmezőbe gépel a felhasználó, ne lapozzunk a nyilakkal!
        if (document.activeElement === searchInput) {
            if (e.key === 'Escape') {
                clearSearch();
            }
            return;
        }

        if (e.key === 'ArrowLeft') {
            prevMovie();
        } else if (e.key === 'ArrowRight') {
            nextMovie();
        }
    });
});