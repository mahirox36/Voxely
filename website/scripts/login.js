function toggleForm() {
    const container = document.getElementById('container');
    container.classList.toggle('right-panel-active');
}

function showError(formId, message) {
    const errorElement = document.getElementById(formId + 'Error');
    errorElement.textContent = message;
    errorElement.classList.add('show');
}

function hideError(formId) {
    const errorElement = document.getElementById(formId + 'Error');
    errorElement.classList.remove('show');
}

document.getElementById('loginForm').addEventListener('submit', function(e) {
    e.preventDefault();
    let name = document.getElementById('nameLog').value;
    let pass = document.getElementById('passLog').value;
    hideError('login');

    fetch('http://localhost:8001/loginpost', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: name,
            password: pass
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
        if (data.success) {
            window.location.href = '/dashboard';  // Redirect to dashboard
        } else {
            showError('login', data.message || 'Login failed. Please try again.');
        }
    })
    .catch(error => {
        showError('login', 'An error occurred. Please try again later.');
    });
});

document.getElementById('registerForm').addEventListener('submit', function(e) {
    e.preventDefault();
    let name = document.getElementById('nameReg').value;
    let pass = document.getElementById('passReg').value;
    hideError('register');

    fetch('http://localhost:8001/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: name,
            password: pass
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/dashboard';  // Redirect to dashboard
        } else {
            showError('register', data.message || 'Registration failed. Please try again.');
        }
    })
    .catch(error => {
        showError('register', 'An error occurred. Please try again later.');
    });
});