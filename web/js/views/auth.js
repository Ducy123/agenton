const AuthViews = (() => {
  function renderLogin(root) {
    root.innerHTML = `
      <div class="card card-auth">
        <div class="brand" style="margin-bottom: var(--space-6)">
          <span class="brand-mark"></span> AgentOn
        </div>
        <h2>Welcome back</h2>
        <p>Sign in to rent and manage your agents.</p>
        <form id="login-form">
          <div class="field">
            <label for="email">Email</label>
            <input type="email" id="email" required autocomplete="email" />
          </div>
          <div class="field">
            <label for="password">Password</label>
            <input type="password" id="password" required autocomplete="current-password" />
          </div>
          <button type="submit" class="btn btn-primary btn-block">Sign in</button>
        </form>
        <p style="margin-top: var(--space-5); text-align:center;">
          No account yet? <a href="#/register">Create one</a>
        </p>
      </div>
    `;

    root.querySelector("#login-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = root.querySelector("#email").value.trim();
      const password = root.querySelector("#password").value;
      try {
        const { access_token } = await AgentOnAPI.login(email, password);
        AgentOnAPI.setToken(access_token);
        Toast.info("Signed in");
        window.location.hash = "#/marketplace";
      } catch (err) {
        Toast.error(err.message);
      }
    });
  }

  function renderRegister(root) {
    root.innerHTML = `
      <div class="card card-auth">
        <div class="brand" style="margin-bottom: var(--space-6)">
          <span class="brand-mark"></span> AgentOn
        </div>
        <h2>Create your account</h2>
        <p>Start renting AI agents in minutes.</p>
        <form id="register-form">
          <div class="field">
            <label for="name">Display name</label>
            <input type="text" id="name" autocomplete="name" />
          </div>
          <div class="field">
            <label for="email">Email</label>
            <input type="email" id="email" required autocomplete="email" />
          </div>
          <div class="field">
            <label for="password">Password</label>
            <input type="password" id="password" required minlength="8" maxlength="72" autocomplete="new-password" />
            <span class="field-hint">At least 8 characters.</span>
          </div>
          <button type="submit" class="btn btn-primary btn-block">Create account</button>
        </form>
        <p style="margin-top: var(--space-5); text-align:center;">
          Already have an account? <a href="#/login">Sign in</a>
        </p>
      </div>
    `;

    root.querySelector("#register-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = root.querySelector("#email").value.trim();
      const password = root.querySelector("#password").value;
      const displayName = root.querySelector("#name").value.trim();
      try {
        await AgentOnAPI.register(email, password, displayName);
        const { access_token } = await AgentOnAPI.login(email, password);
        AgentOnAPI.setToken(access_token);
        Toast.info("Account created");
        window.location.hash = "#/marketplace";
      } catch (err) {
        Toast.error(err.message);
      }
    });
  }

  return { renderLogin, renderRegister };
})();
