// Initialize the map
const map = L.map('map').setView([55.6761, 12.5683], 7); // Use default coordinates
const customIcon = L.icon({
    iconUrl: markerIconUrl,
    iconSize: [25, 41],
    });


    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Store markers with their IDs
    const markers = {};

    // Fetch carpool locations from API
    function loadCarpoolLocations() {
    const url = '/api/carpool-locations' + window.location.search; // This will include any query parameters like ?club=xxx

    fetch(url)
        .then(response => response.json())
        .then(carpools => {
            // Add markers for each carpool
            carpools.forEach(carpool => {
                const marker = L.marker([carpool.latitude, carpool.longitude], { icon: customIcon })
                    .addTo(map)
                    .bindPopup(`
                        <strong>${carpool.event}</strong><br>
                        From: ${carpool.departure_place}<br>
                        Time: ${carpool.departure_time}<br>
                        Available seats: ${carpool.vacant_seats}<br>
                        <a href="#carpool-${carpool.id}">View details</a>
                    `);

                // Store marker reference with carpool ID
                markers[carpool.id] = marker;

                // Add ID to corresponding carpool card
                const carpoolCard = document.querySelector(`.carpool-card[data-id="${carpool.id}"]`);
                if (carpoolCard) {
                    carpoolCard.id = `carpool-${carpool.id}`;
                }
            });

            // If there are carpools, fit map bounds to include all markers
            if (carpools.length > 0) {
                const bounds = [];
                carpools.forEach(carpool => {
                    bounds.push([carpool.latitude, carpool.longitude]);
                });
                map.fitBounds(bounds);
            }
        })
        .catch(error => console.error('Error loading carpool locations:', error));
}

// Load carpools when the document is ready
document.addEventListener('DOMContentLoaded', function () {
    loadCarpoolLocations();

    // Add event listeners to "Show on map" buttons
    document.querySelectorAll('.locate-btn').forEach(button => {
        button.addEventListener('click', function () {
            const lat = parseFloat(this.getAttribute('data-lat'));
            const lng = parseFloat(this.getAttribute('data-lng'));

            // Center map on location
            map.setView([lat, lng], 12);

            // Find the marker for this carpool and open its popup
            const carpoolId = parseInt(this.closest('.carpool-card').getAttribute('data-id'));
            if (markers[carpoolId]) {
                markers[carpoolId].openPopup();
            }
        });
    });
});