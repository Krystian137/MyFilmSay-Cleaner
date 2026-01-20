document.addEventListener("DOMContentLoaded", function () {
    initializeReplyToggle();
    initializeVoteButtons();
    initializeDeleteButtons();
    initializeFlashMessages();
    initializeScrollListener();
    initializeProgressCircles();
    initializeSortMenu();
});

// Reply Comment Toggle
function initializeReplyToggle() {
    document.querySelectorAll('.reply-comment').forEach(button => {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            const container = this.closest('.commentText');
            const replyForm = container.querySelector('.reply-form');
            if (replyForm) {
                replyForm.style.display = (replyForm.style.display === 'none' || replyForm.style.display === '') ? 'block' : 'none';
            }
        });
    });
}

// Vote Comment handlers
function initializeVoteButtons() {
    document.querySelectorAll('.vote-button').forEach(button => {
        button.addEventListener('click', function () {
            const btn = this;
            const wrapper = btn.parentElement;

            const commentId = btn.dataset.commentId.replace('comment-', '');

            fetch(btn.dataset.url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    comment_id: commentId,
                    vote_type: btn.dataset.voteType
                })
            })
            .then(res => {
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                if (!data.success) {
                    console.error('Vote failed:', data.error);
                    return;
                }

                const likeBtn = wrapper.querySelector('[data-vote-type="like"]');
                const dislikeBtn = wrapper.querySelector('[data-vote-type="dislike"]');

                likeBtn.innerHTML = `Like (${data.likes})`;
                dislikeBtn.innerHTML = `Dislike (${data.dislikes})`;
            })
            .catch(err => {
                console.error('Vote error:', err);
            });
        });
    });
}

// Delete Comment handlers
function initializeDeleteButtons() {
    document.querySelectorAll('.delete-comment').forEach(button => {
        button.addEventListener('click', function () {
            const commentId = this.dataset.commentId;
            const url = this.dataset.url;

            if (!confirm('Na pewno usunąć komentarz?')) return;

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;

                const el = document.getElementById(`comment-${commentId}`);
                if (el) el.remove();
            });
        });
    });
}

// Edit Comment handlers
document.addEventListener('click', function(e) {
    // Show edit form
    if (e.target.classList.contains('edit-comment-btn')) {
        e.preventDefault();
        const commentId = e.target.dataset.commentId;
        document.querySelector(`.comment-display-${commentId}`).style.display = 'none';
        document.querySelector(`.edit-form-${commentId}`).style.display = 'block';
    }

    // Cancel edit
    if (e.target.classList.contains('cancel-edit-comment')) {
        const commentId = e.target.dataset.commentId;
        document.querySelector(`.comment-display-${commentId}`).style.display = 'block';
        document.querySelector(`.edit-form-${commentId}`).style.display = 'none';
    }

    // Save edit
    if (e.target.classList.contains('save-edit-comment')) {
        const commentId = e.target.dataset.commentId;
        const url = e.target.dataset.url; // Użyj URL z template zamiast budować ręcznie

        console.log('Trying to edit comment:', commentId);
        console.log('URL from template:', url);
        console.log('CSRF Token:', getCookie('csrftoken'));

        const newText = document.querySelector(`.edit-form-${commentId} .edit-textarea`).value;

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ text: newText })
        })
        .then(res => {
            console.log('Response status:', res.status);
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            console.log('Response data:', data);
            if (data.success) {
                const displayElement = document.querySelector(`.comment-display-${commentId}`);
                displayElement.textContent = newText;
                displayElement.style.display = 'block';
                document.querySelector(`.edit-form-${commentId}`).style.display = 'none';
            } else {
                alert(data.message || 'Failed to update comment');
            }
        })
        .catch(err => {
            console.error('Edit error:', err);
            alert('Error updating comment: ' + err.message);
        });
    }
});

// Flash Messages handlers
function initializeFlashMessages() {
    setTimeout(function () {
        var flashMessages = document.querySelectorAll('.flash-messages .alert');
        flashMessages.forEach(function (message) {
            message.style.transition = "opacity 1s ease";
            message.style.opacity = 0;
            setTimeout(function () {
                message.remove();
            }, 1000);
        });
    }, 5000);

    var closeButtons = document.querySelectorAll('.flash-messages .close, .flash-messages .btn-close');
    closeButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            var alert = this.closest('.alert');
            alert.style.transition = "opacity 1s ease";
            alert.style.opacity = 0;
            setTimeout(function () {
                alert.remove();
            }, 1000);
        });
    });
}

// Scroll Listener for Navigation Bar
function initializeScrollListener() {
    let scrollPos = 0;
    const mainNav = document.getElementById('mainNav');
    if (!mainNav) return;
    const headerHeight = mainNav.clientHeight;

    window.addEventListener('scroll', function () {
        const currentTop = document.body.getBoundingClientRect().top * -1;

        if (currentTop < scrollPos) {
            if (currentTop > 0 && mainNav.classList.contains('is-fixed')) {
                mainNav.classList.add('is-visible');
            } else {
                mainNav.classList.remove('is-visible', 'is-fixed');
            }
        } else {
            mainNav.classList.remove('is-visible');
            if (currentTop > headerHeight && !mainNav.classList.contains('is-fixed')) {
                mainNav.classList.add('is-fixed');
            }
        }
        scrollPos = currentTop;
    });
}

// Progress Circles Initialization
function initializeProgressCircles() {
    const circles = document.querySelectorAll('.progress-circle');
    circles.forEach(circle => {
        const percentage = circle.dataset.percentage;
        const progress = circle.querySelector('.progress-circle__progress');
        const radius = 15.9155;
        const circumference = radius * 2 * Math.PI;
        const offset = circumference - (percentage / 100 * circumference);

        progress.style.strokeDasharray = `${circumference} ${circumference}`;
        progress.style.strokeDashoffset = offset;
    });
}

// Sort Menu Toggle
function initializeSortMenu() {
    const sortButton = document.getElementById('sortButton');
    const sortMenu = document.getElementById('sortMenu');

    if (sortButton && sortMenu) {
        sortButton.addEventListener('click', function () {
            sortMenu.style.display = sortMenu.style.display === 'none' || sortMenu.style.display === '' ? 'block' : 'none';
        });

        document.addEventListener('click', function (event) {
            if (!sortButton.contains(event.target) && !sortMenu.contains(event.target)) {
                sortMenu.style.display = 'none';
            }
        });
    }
}

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}