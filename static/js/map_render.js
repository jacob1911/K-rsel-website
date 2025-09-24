// Initialize the map
const map = L.map('map', {
    dragging: true,
    tap: false
}

).setView([55.6761, 12.5683], 7);

// Custom icons
const customIcon = L.icon({
    iconUrl: markerIconUrl,
    iconSize: [41, 41],
});
const customIcon2 = L.icon({
    iconUrl: markerIconUrl2,
    iconSize: [41, 41],
});



// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Track carpool markers and connecting lines
const markers = {};
let lines = [];
let activeRaceId = null;


// Scroll map into view
function scrollToMap() {
    const mapSection = document.getElementById("map");
    if (mapSection) mapSection.scrollIntoView({ behavior: "smooth" });
}

// Remove all carpool markers
function removeAllCarpoolMarkers() {
    Object.values(markers).forEach(marker => map.removeLayer(marker));
    Object.keys(markers).forEach(key => delete markers[key]);
}

// Remove all lines
// function removeAllLines() {
//     lines.forEach(line => map.removeLayer(line));
//     lines = [];
// }

// Toggle carpools for a specific race
function toggleCarpools(raceId, raceLat, raceLng) {
    if (activeRaceId === raceId) {
        removeAllCarpoolMarkers();
        removeAllLines();
        activeRaceId = null;
        return;
    }
    console.log("Se mig", raceId)
    loadCarpoolsForRace(raceId, raceLat, raceLng);
    activeRaceId = raceId;
}

// Load carpools for a specific race
function loadCarpoolsForRace(raceId, raceLat, raceLng) {
    const url = `/api/carpool-locations?race_id=${raceId}`;

    fetch(url)
        .then(response => response.json())
        .then(carpools => {
            removeAllCarpoolMarkers();
            removeAllLines();

            carpools.forEach(carpool => {
                console.log("carpool: ", carpool.name)

                const marker = L.marker([carpool.latitude, carpool.longitude], { icon: customIcon })
                    .addTo(map)


                markers[carpool.id] = marker;

                // === Tegn rute via Leaflet Routing Machine ===
                const router = L.Routing.osrmv1();
                router.route([
                    L.Routing.waypoint([carpool.latitude, carpool.longitude]),
                    L.Routing.waypoint([raceLat, raceLng])
                ], function (err, routes) {
                    if (!err && routes && routes.length > 0) {
                        const route = routes[0];
                        const durationMin = Math.round(route.summary.totalTime / 60); // in minutes
                        console.log(`Travel time from carpool ${carpool.id} to race: ${durationMin} min`);

                        // Optionally, draw the line on the map
                        const line = L.polyline(route.coordinates.map(c => [c.lat, c.lng]), {
                            color: 'blue',
                            weight: 2,
                            opacity: 0.6
                        }).addTo(map);

                        lines.push(line);

                        // You could also add duration to the popup
                        markers[carpool.id].bindPopup(`
            <strong>${carpool.event}</strong><br>
            Ejer: ${carpool.owner}<br>
            Afgang: ${carpool.departure_time}<br>
            Ledige pladser: ${carpool.vacant_seats}<br>
            Estimeret rejsetid: ${durationMin} min<br>
            <a href="#" onclick="scrollToCarpoolCard(${carpool.id}); return false;">Vis detaljer</a>
        `);

                    }
                });
            });

            // Fit map to show all carpools and race
            if (carpools.length > 0) {
                const bounds = carpools.map(c => [c.latitude, c.longitude]);
                bounds.push([raceLat, raceLng]);
                map.fitBounds(bounds);
            }
        })
        .catch(error => console.error('Error loading carpools:', error));
}

function scrollToCarpoolCard(carpoolId) {
    const card = document.querySelector(`.carpool-card[data-id='${carpoolId}']`);
    if (card) {
        console.log("scrolling")
        card.scrollIntoView({ behavior: "smooth", block: "center" });
        card.classList.add('highlight');
        setTimeout(() => card.classList.remove('highlight'), 1500);
    }
}

function removeAllLines() {
    lines.forEach(line => map.removeLayer(line));
    lines = [];
}

function setCarpoolQuery(carpoolId) {
    const url = new URL(window.location);
    url.searchParams.set("race_id", carpoolId);
    window.history.pushState({}, "", url);
    const raceInput = document.getElementById('race_id_input');
    // console.log("UPDATET", raceInput)
    // raceInput.value = carpoolId;

}

// Load races and add markers with "Show Carpools" button
function loadRaceLocations() {
    const url = '/api/race-details' + window.location.search;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            let filteredRaces;
            let opret_klub_carpool;
            let club_id = 0;

            if (window.location.pathname.includes('/club-dashboard')) {
                opret_klub_carpool = true;
                filteredRaces = data.races.filter(race => race.club_level === true && race.club_id === data.session_club_id);
                club_id = data.session_club_id;
            } else {
                opret_klub_carpool = false;
                filteredRaces = data.races.filter(race => race.club_level === false);
            }

            // Get race_id from URL if present
            const params = new URLSearchParams(window.location.search);
            const urlRaceId = params.get("race_id");

            filteredRaces.forEach(race => {
                const marker = L.marker([race.latitude, race.longitude], { icon: customIcon2 })
                    .addTo(map);

                const popupHtml = `
                <strong>${race.name}</strong><br>
                Beskrivelse: ${race.description}<br>
                Dato: ${race.date}<br>
                ${race.carpools.length > 0
                        ? `<button onclick="setCarpoolQuery(${race.id})" class="show-carpools" data-race-id="${race.id}" data-lat="${race.latitude}" data-lng="${race.longitude}">Vis carpools</button>`
                        : `<em>Ingen carpools endnu</em><br>`}
                <button onclick="window.location.href='/create?event=${encodeURIComponent(race.name)}&race_id=${race.id}&is_club=${opret_klub_carpool}&date=${race.date}&club_id=${club_id}'">Opret carpool</button>
                `;

                marker.bindPopup(popupHtml);

                marker.on('popupopen', function (e) {
                    const popupEl = e.popup.getElement();
                    const showBtn = popupEl.querySelector('.show-carpools');
                    if (showBtn) {
                        showBtn.addEventListener('click', function () {
                            const raceId = this.dataset.raceId;
                            const lat = parseFloat(this.dataset.lat);
                            const lng = parseFloat(this.dataset.lng);
                            showCarpoolCardsForRace(parseInt(raceId));
                            toggleCarpools(raceId, lat, lng);
                            const raceInput = document.getElementById('race_id_input');
                            console.log("UPDATET")
                            raceInput.value = this.dataset.raceId;
                        });
                    }
                });

                // 🔹 If race_id matches the URL, open popup and toggle carpools
                if (urlRaceId && parseInt(urlRaceId) === race.id) {
                    marker.openPopup();
                    if (race.carpools.length > 0) {
                        showCarpoolCardsForRace(race.id);
                        toggleCarpools(race.id, race.latitude, race.longitude);
                    }
                    map.setView([race.latitude, race.longitude], 13);
                }
            });
        })
        .catch(error => console.error('Error loading race locations:', error));
}


function showCarpoolCardsForRace(raceId) {
    // Hent alle carpool-cards
    const cards = document.querySelectorAll('.carpool-card');

    cards.forEach(card => {
        // Hent race_id fra data-attribut
        const cardRaceId = parseInt(card.dataset.raceid);

        if (cardRaceId === raceId) {
            card.style.display = 'block';  // vis card
        } else {
            card.style.display = 'none';   // skjul card
        }
    });
}


// Initialize map after DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    loadRaceLocations();

    // Locate button on carpools
    document.querySelectorAll('.locate-btn').forEach(button => {
        button.addEventListener('click', function () {
            const lat = parseFloat(this.getAttribute('data-lat'));
            const lng = parseFloat(this.getAttribute('data-lng'));

            map.setView([lat, lng], 12);

            const carpoolId = parseInt(this.closest('.carpool-card').getAttribute('data-id'));
            if (markers[carpoolId]) markers[carpoolId].openPopup();
        });
    });
    const params = new URLSearchParams(window.location.search);
    const carpoolId = params.get("carpool_id");

    if (carpoolId) {
        console.log("HEJR")
        showCarpoolCardsForRace(carpoolId);
        // url = `/api/race-details?race_id=${carpoolId}`
        // fetch(url)
        //     .then(response => response.json())   // parse JSON
        //     .then(data => {
        //         // data is an array
        //         const lat = parseFloat(data[0].latitude);
        //         const lng = parseFloat(data[0].longitude);

        //         console.log("Lat:", lat, "Lng:", lng);
        //         toggleCarpools(carpoolId, lat, lng);
        //         showCarpoolCardsForRace(carpoolId);

        //     })
        //     .catch(err => console.error(err));
        // your own function to open/highlight it
    }
});


