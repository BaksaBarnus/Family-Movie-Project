async function db_fetch() {
    try {
        const response = await fetch('api/movies');
        const movies = await response.json();

        const tbody = document.getElementById('movie_row');
        tbody.innerHTML = '';

        movies.forEach(movie => {
            const row = document.createElement('tr');
            const title = document.createElement('td');
            const year = document.createElement('td');

            title.innerHTML = movie.clean_title;
            year.innerHTML = movie.year ? movie.year : 'N/A';

            row.appendChild(title)
            row.appendChild(year)
            tbody.appendChild(row)
        });
    } catch (error) {
        console.error('Hiba a betöltések közben', error)
    }
}

document.addEventListener('DOMContentLoaded', db_fetch);