<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>Registrieren</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  {% include 'navbar.html' %}
  <div class="login-container">
    <h2>Registrierung</h2>
    <form action="{{ url_for('register') }}" method="POST">
      <label>Benutzername:</label><br>
      <input type="text" name="username" required><br>

      <label>E-Mail (optional):</label><br>
      <input type="email" name="email"><br>

      <label>Passwort:</label><br>
      <input type="password" name="password" required><br>

      <button type="submit">Registrieren</button>
    </form>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, msg in messages %}
          <p class="flash {{ category }}">{{ msg }}</p>
        {% endfor %}
      {% endif %}
    {% endwith %}
  </div>
  {% include 'footer.html' %}
</body>
</html>
