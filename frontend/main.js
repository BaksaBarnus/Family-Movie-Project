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
    const mainTitle = movie.tmdb_title || movie.clean_title || 'Cím nélkül';

    if (movie.original_title && movie.original_title.toLowerCase() !== mainTitle.toLowerCase()) {
        movieTitle.innerHTML = `${mainTitle} <span class="original-title">(${movie.original_title})</span>`;
    } else {
        movieTitle.textContent = mainTitle;
    }

    movieYear.textContent = movie.year ? movie.year : '----';
    movieRating.textContent = movie.rating ? `⭐ ${Number(movie.rating).toFixed(1)}` : '⭐ N/A';

    // Műfajok megjelenítése
    if (movie.genres) {
        movieGenres.textContent = movie.genres;
        movieGenres.style.display = 'inline-block';
    } else {
        movieGenres.style.display = 'none';
    }

    // Szöveges adatok kitöltése (A DUPLIKÁLT CÍM/ÉV/RATING SOROKAT KITAKARÍTOTTUK INNEN!)
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

        // HA A KÉP SIKERESEN BETÖLTŐDÖTT:
        posterImg.onload = () => {
            posterImg.classList.remove('hidden');
            posterPlaceholder.style.display = 'none';
        };

        // HA A KÉP BETÖLTÉSE SIKERTELEN (pl. AdBlocker vagy nincs net):
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

// ==========================================================================
// KÍVÁNSÁGLISTA ELEMEK ÉS LOGIKA
// ==========================================================================
const wishlistToggleBtn = document.getElementById("wishlist-toggle-btn");
const wishlistModal = document.getElementById("wishlist-modal");
const closeWishlistBtn = document.getElementById("close-wishlist-btn");
const wishlistForm = document.getElementById("wishlist-form");
const wishlistInput = document.getElementById("wishlist-input");
const wishlistList = document.getElementById("wishlist-list");

async function fetchWishlist() {
  try {
    const res = await fetch("/api/wishlist");
    const items = await res.json();
    renderWishlist(items);
  } catch (e) {
    console.error("Kívánságlista betöltési hiba:", e);
  }
}

// Lista kirajzolása
function renderWishlist(items) {
  wishlistList.innerHTML = "";
  if (items.length === 0) {
    wishlistList.innerHTML =
      '<li style="color: var(--text-muted); text-align: center; padding: 10px;">Még nincs kért film a listában.</li>';
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "wishlist-item";
    li.innerHTML = `
            <span>${item.title}</span>
            <button class="delete-item-btn" data-id="${item.id}" title="Törlés">🗑️</button>
        `;
    wishlistList.appendChild(li);
  });

  // Törlés gombok eseményei
  wishlistList.querySelectorAll(".delete-item-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const id = e.target.getAttribute("data-id");
      await deleteWishlistItem(id);
    });
  });
}

// Új film hozzáadása
async function addWishlistItem(title) {
  try {
    const res = await fetch("/api/wishlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (res.ok) {
      wishlistInput.value = "";
      fetchWishlist();
    }
  } catch (e) {
    console.error("Hiba a hozzáadáskor:", e);
  }
}

// Film törlése
async function deleteWishlistItem(id) {
  try {
    const res = await fetch(`/api/wishlist?id=${id}`, {
      method: "DELETE",
    });
    if (res.ok) {
      fetchWishlist();
    }
  } catch (e) {
    console.error("Hiba a törléskor:", e);
  }
}

// Felugró ablak megnyitása / bezárása
wishlistToggleBtn.addEventListener("click", () => {
  wishlistModal.classList.remove("hidden");
  fetchWishlist();
});

closeWishlistBtn.addEventListener("click", () => {
  wishlistModal.classList.add("hidden");
});

wishlistModal.addEventListener("click", (e) => {
  if (e.target === wishlistModal) {
    wishlistModal.classList.add("hidden");
  }
});

wishlistForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const title = wishlistInput.value.trim();
  if (title) addWishlistItem(title);
});