// Initialize the map
const map = L.map('map').setView([55.6761, 12.5683], 7);

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
function removeAllLines() {
    lines.forEach(line => map.removeLayer(line));
    lines = [];
}

// Toggle carpools for a specific race
function toggleCarpools(raceId, raceLat, raceLng) {
    if (activeRaceId === raceId) {
        removeAllCarpoolMarkers();
        removeAllLines();
        activeRaceId = null;
        return;
    }

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
                const marker = L.marker([carpool.latitude, carpool.longitude], { icon: customIcon })
                    .addTo(map)
                    .bindPopup(`
                        <strong>${carpool.event}</strong><br>
                        Fra: ${carpool.departure_place}<br>
                        Afgang: ${carpool.departure_time}<br>
                        Ledige pladser: ${carpool.vacant_seats}<br>
                        <a href="#carpool-${carpool.id}">Vis detaljer</a>
                    `);

                markers[carpool.id] = marker;

                // Draw a line from race to this carpool
                const line = L.polyline([[raceLat, raceLng], [carpool.latitude, carpool.longitude]], {
                    color: 'blue',
                    weight: 2,
                    opacity: 0.6
                }).addTo(map);

                lines.push(line);
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

// Load races and add markers with "Show Carpools" button
function loadRaceLocations() {
    const url = '/api/race-details' + window.location.search;

    fetch(url)
    .then(response => response.json())
    .then(races => {
        races.forEach(race => {
            const marker = L.marker([race.latitude, race.longitude], { icon: customIcon2 })
                .addTo(map);
                
            if (race.carpools.length > 0) {
                marker.bindPopup(`
                    <strong>${race.name}</strong><br>
                    Beskrivelse: ${race.description}<br>
                    Dato: ${race.date}<br>
                    <button onclick="toggleCarpools(${race.id}, ${race.latitude}, ${race.longitude})">Vis carpools</button>
                    <button onclick="window.location.href='/create?event=${encodeURIComponent(race.name)}&race_id=${race.id}'">Opret carpool</button>
                `);
            } else {
                marker.bindPopup(`
                    <strong>${race.name}</strong><br>
                    Beskrivelse: ${race.description}<br>
                    Dato: ${race.date}<br>
                    <em>Ingen carpools endnu</em><br>
                    <button onclick="window.location.href='/create?event=${encodeURIComponent(race.name)}&race_id=${race.id}'">Opret carpool</button>
                `);
            }
        });
    })
    .catch(error => console.error('Error loading race locations:', error));
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
});
