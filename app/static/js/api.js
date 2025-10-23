/**
 * common api request function
 */
async function apiRequest(url, method = 'GET', data = null, isFormData = false) {
    const options = {
        method: method,
        credentials: 'same-origin'
    };

    if (data) {
        if (isFormData) {
            // if request data form is formData，don't need to set Content-Type here
            options.body = data;
        } else if (['POST', 'PUT', 'PATCH'].includes(method)) {
            // if request data form is json, set Contnet-Type here
            options.headers = {
                'Content-Type': 'application/json',
            };
            options.body = JSON.stringify(data);
            console.log('Request body:', options.body); // 调试日志
        }
    }

    try {
        console.log('Making request to:', url); // 调试日志
        console.log('Request options:', options); // 调试日志
        const response = await fetch(url, options);
        
        // handle error code 401
        if (response.status === 401) {
            const result = await response.json();
            showMessage(result.error || 'please login to continue', 'error');
            // set time out and send error msg to users
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
            throw new Error('please login to continue');
        }

        const result = await response.json();
        console.log('Response:', result); // 调试日志

        if (result.success) {
            return result;
        } else {
            throw new Error(result.message || 'request failed');
        }
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

/**
 * Display a Bootstrap Toast message
 * @param {string} message - message content
 * @param {string} type - message type: 'success' or 'error'
 */
function showMessage(message, type = 'success') {

    // create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center rounded-3 flash ${type === 'success' ? 'text-success border-success' : 'text-danger border-danger'}`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.setAttribute('data-bs-autohide', 'true');

    // create toast content
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    // append toast element to toast container
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        // if toast container not exist, create it
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed top-50 start-50 translate-middle p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    document.getElementById('toast-container').appendChild(toastEl);

    // initialize toast
    const toast = new bootstrap.Toast(toastEl, {
        delay: 3000, // 3 seconds delay
        animation: true
    });

    // display toast
    toast.show();

    // hide toast and remove element when hidden
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
}

/**
 * Navigate to journey detail page
 * @param {string} journeyId - The ID of the journey
 */
function goToJourneyDetail(journeyId) {
    window.location.href = `/journey/detail/${journeyId}`;
}
