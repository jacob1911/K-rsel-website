// Add this JavaScript to your template or create a new static/js file

function formatDateTime(timestamp) {
  const date = new Date(timestamp);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0'); // Months start at 0
  const dd = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd} ${hh}:${min}`;


}

document.addEventListener('DOMContentLoaded', function() {
    // Find all comment forms on the page
    const commentForms = document.querySelectorAll('.comment-form');


    // Add event listeners to each form
    commentForms.forEach(form => {
      form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const carpoolId = this.getAttribute('data-carpool-id');
        const authorInput = this.querySelector('input[name="author"]');
        const textInput = this.querySelector('textarea[name="text"]');
        
        // Create FormData object
        const formData = new FormData();
        formData.append('author', authorInput.value);
        formData.append('text', textInput.value);
        
        // Send AJAX request
        fetch(`/add_comment/${carpoolId}`, {
          method: 'POST',
          body: formData
        })
        .then(response => response.text())
        .then(html => {
          // Clear form inputs
          authorInput.value = '';
          textInput.value = '';
          
          // Fetch updated comments for this specific carpool
          fetch(`/get_comments/${carpoolId}`)
            .then(response => response.json())
            .then(comments => {
              // Update comments section for this carpool only
              const commentsContainer = document.querySelector(`#comments-${carpoolId}`);
              commentsContainer.innerHTML = '';
              
             
              comments.forEach(comment => {
                const commentElement = document.createElement('div');
                commentElement.className = 'comment';
                commentElement.innerHTML = `
                  <strong>${comment.author}</strong> - ${formatDateTime(comment.timestamp)}<br>
                  <p>${comment.text}</p>
                `;
                commentsContainer.appendChild(commentElement);
              });
            });
        })
        .catch(error => console.error('Error:', error));
      });
    });
  });