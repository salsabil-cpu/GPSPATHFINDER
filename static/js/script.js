// Wait for the DOM to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const getLocationBtn = document.getElementById('getLocationBtn');
    const startLatInput = document.getElementById('start_lat');
    const startLngInput = document.getElementById('start_lng');
    const addWaypointBtn = document.getElementById('addWaypointBtn');
    const waypointsContainer = document.getElementById('waypointsContainer');
    const waypointTemplate = document.getElementById('waypointTemplate');
    const uploadExcelBtn = document.getElementById('uploadExcelBtn');
    const excelFileInput = document.getElementById('excelFile');
    const excelUploadResult = document.getElementById('excelUploadResult');
    
    // Get current location when button is clicked
    if (getLocationBtn) {
        getLocationBtn.addEventListener('click', function() {
            if (navigator.geolocation) {
                getLocationBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Getting location...';
                getLocationBtn.disabled = true;
                
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        // Success callback
                        startLatInput.value = position.coords.latitude.toFixed(6);
                        startLngInput.value = position.coords.longitude.toFixed(6);
                        
                        getLocationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Get Current Location';
                        getLocationBtn.disabled = false;
                    },
                    function(error) {
                        // Error callback
                        let errorMessage = 'Unable to retrieve your location. ';
                        
                        switch(error.code) {
                            case error.PERMISSION_DENIED:
                                errorMessage += 'User denied the request for Geolocation.';
                                break;
                            case error.POSITION_UNAVAILABLE:
                                errorMessage += 'Location information is unavailable.';
                                break;
                            case error.TIMEOUT:
                                errorMessage += 'The request to get user location timed out.';
                                break;
                            case error.UNKNOWN_ERROR:
                                errorMessage += 'An unknown error occurred.';
                                break;
                        }
                        
                        alert(errorMessage);
                        getLocationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Get Current Location';
                        getLocationBtn.disabled = false;
                    }
                );
            } else {
                alert('Geolocation is not supported by this browser.');
            }
        });
    }
    
    // Add waypoint when button is clicked
    if (addWaypointBtn) {
        addWaypointBtn.addEventListener('click', function() {
            addWaypoint();
        });
    }
    
    // Handle Excel file upload
    if (uploadExcelBtn) {
        uploadExcelBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('excelFile');
            if (!fileInput.files.length) {
                excelUploadResult.innerHTML = `
                    <div class="alert alert-danger">
                        Please select a file to upload
                    </div>
                `;
                return;
            }
            
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            excelUploadResult.innerHTML = `
                <div class="alert alert-info">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                        Uploading and processing file...
                    </div>
                </div>
            `;
            
            fetch('/upload_excel', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    excelUploadResult.innerHTML = `
                        <div class="alert alert-danger">
                            ${data.error}
                        </div>
                    `;
                } else if (data.waypoints && data.waypoints.length > 0) {
                    // Clear existing waypoints
                    waypointsContainer.innerHTML = '';
                    
                    // Add waypoints from the uploaded file
                    data.waypoints.forEach(point => {
                        addWaypoint(point.name, point.lat, point.lng);
                    });
                    
                    excelUploadResult.innerHTML = `
                        <div class="alert alert-success">
                            Successfully imported ${data.waypoints.length} waypoints
                        </div>
                    `;
                    
                    // Close modal after a delay
                    setTimeout(() => {
                        const modal = bootstrap.Modal.getInstance(document.getElementById('excelImportModal'));
                        if (modal) {
                            modal.hide();
                        }
                    }, 1500);
                } else {
                    excelUploadResult.innerHTML = `
                        <div class="alert alert-warning">
                            No valid waypoints found in the file
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                excelUploadResult.innerHTML = `
                    <div class="alert alert-danger">
                        Error uploading file: ${error.message}
                    </div>
                `;
            });
        });
    }
    
    // Function to add a new waypoint to the form
    function addWaypoint(name = '', lat = '', lng = '') {
        const waypointNode = document.importNode(waypointTemplate.content, true);
        const waypointElement = waypointNode.querySelector('.waypoint-item');
        
        // Set values if provided
        waypointNode.querySelector('.waypoint-name').value = name;
        waypointNode.querySelector('.waypoint-lat').value = lat;
        waypointNode.querySelector('.waypoint-lng').value = lng;
        
        // Set up remove button functionality
        const removeBtn = waypointNode.querySelector('.remove-waypoint');
        removeBtn.addEventListener('click', function() {
            waypointElement.remove();
        });
        
        // Add waypoint to container
        waypointsContainer.appendChild(waypointNode);
    }
    
    // Add one waypoint by default if the container is empty
    if (waypointsContainer && waypointsContainer.children.length === 0) {
        addWaypoint();
    }
    
    // Form validation
    const routeForm = document.getElementById('routeForm');
    if (routeForm) {
        routeForm.addEventListener('submit', function(event) {
            const startLat = parseFloat(startLatInput.value);
            const startLng = parseFloat(startLngInput.value);
            
            // Validate starting coordinates
            if (isNaN(startLat) || isNaN(startLng) || 
                startLat < -90 || startLat > 90 || 
                startLng < -180 || startLng > 180) {
                event.preventDefault();
                alert('Please enter valid starting coordinates (Latitude: -90 to 90, Longitude: -180 to 180)');
                return;
            }
            
            // Validate waypoints
            const waypointItems = document.querySelectorAll('.waypoint-item');
            if (waypointItems.length === 0) {
                event.preventDefault();
                alert('Please add at least one waypoint');
                return;
            }
            
            let hasValidWaypoint = false;
            
            for (const item of waypointItems) {
                const latInput = item.querySelector('.waypoint-lat');
                const lngInput = item.querySelector('.waypoint-lng');
                
                const lat = parseFloat(latInput.value);
                const lng = parseFloat(lngInput.value);
                
                if (!isNaN(lat) && !isNaN(lng) && 
                    lat >= -90 && lat <= 90 && 
                    lng >= -180 && lng <= 180) {
                    hasValidWaypoint = true;
                    break;
                }
            }
            
            if (!hasValidWaypoint) {
                event.preventDefault();
                alert('Please enter valid coordinates for at least one waypoint');
            }
        });
    }
});
