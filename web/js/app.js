(function () {
  const NAV_LINKS = [
    { path: "/marketplace", label: "Marketplace" },
    { path: "/instances", label: "My Instances" },
    { path: "/wallet", label: "Wallet" },
    { path: "/platforms", label: "Connected Accounts" },
  ];

  function renderShell() {
    document.getElementById("app").innerHTML = `
      <div class="app-shell">
        <nav class="app-nav" id="app-nav">
          <div class="brand"><span class="brand-mark"></span> AgentOn</div>
          <div class="nav-links">
            ${NAV_LINKS.map((l) => `<a class="nav-link" data-path="${l.path}" href="#${l.path}">${l.label}</a>`).join("")}
          </div>
          <div class="nav-footer">
            <span id="nav-user" style="font-size: var(--text-sm); color: var(--color-text-muted);"></span>
            <button class="btn btn-ghost btn-sm" id="logout-btn">Sign out</button>
          </div>
        </nav>
        <main class="app-main" id="app-main"></main>
      </div>
    `;

    document.getElementById("logout-btn").addEventListener("click", () => {
      AgentOnAPI.clearToken();
      window.location.hash = "#/login";
    });
  }

  async function updateNav(path, requiresAuth) {
    const nav = document.getElementById("app-nav");
    const main = document.getElementById("app-main");
    if (!requiresAuth) {
      nav.classList.add("hidden");
      main.classList.add("centered");
      return;
    }
    nav.classList.remove("hidden");
    main.classList.remove("centered");
    nav.querySelectorAll(".nav-link").forEach((a) => a.classList.toggle("active", a.dataset.path === path));

    const userEl = document.getElementById("nav-user");
    if (!userEl.dataset.loaded) {
      try {
        const me = await AgentOnAPI.me();
        userEl.textContent = me.display_name || me.email;
        userEl.dataset.loaded = "1";
      } catch {
        /* not fatal — nav still renders without the greeting */
      }
    }
  }

  document.addEventListener("agenton:navigate", (e) => updateNav(e.detail.path, e.detail.requiresAuth));

  renderShell();

  Router.register("/login", AuthViews.renderLogin, { requiresAuth: false });
  Router.register("/register", AuthViews.renderRegister, { requiresAuth: false });
  Router.register("/marketplace", MarketplaceView.render);
  Router.register("/instances", InstancesView.render);
  Router.register("/wallet", WalletView.render);
  Router.register("/platforms", PlatformsView.render);

  Router.init(document.getElementById("app-main"));
})();
