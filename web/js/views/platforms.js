const PlatformsView = (() => {
  const PROVIDERS = [
    { key: "twitter", label: "X (Twitter)", scopeHint: "Lets rented agents follow, like, retweet, and post on your behalf." },
    { key: "discord", label: "Discord", scopeHint: "Lets rented agents join a server on your behalf." },
  ];

  async function render(root) {
    root.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Connected accounts</h1>
          <p>Connect once — every rented agent that needs it reuses this connection automatically.</p>
        </div>
      </div>
      <div id="provider-cards" class="bento-grid"></div>
    `;

    const cardsEl = root.querySelector("#provider-cards");

    async function refresh() {
      let connections = [];
      try {
        connections = await AgentOnAPI.get("/platforms");
      } catch (err) {
        Toast.error(err.message);
      }
      const byProvider = Object.fromEntries(connections.map((c) => [c.provider, c]));

      cardsEl.innerHTML = PROVIDERS.map((p) => {
        const conn = byProvider[p.key];
        return `
          <div class="card">
            <h3>${p.label}</h3>
            <p>${p.scopeHint}</p>
            ${
              conn
                ? `<span class="badge badge-running">Connected</span>
                   <p class="mono" style="margin-top: var(--space-3);">as ${conn.provider_user_id}</p>
                   <button class="btn btn-danger btn-block" data-disconnect="${p.key}">Disconnect</button>`
                : `<button class="btn btn-primary btn-block" data-connect="${p.key}">Connect ${p.label}</button>`
            }
          </div>`;
      }).join("");

      cardsEl.querySelectorAll("[data-connect]").forEach((btn) => {
        btn.addEventListener("click", () => connect(btn.dataset.connect));
      });
      cardsEl.querySelectorAll("[data-disconnect]").forEach((btn) => {
        btn.addEventListener("click", () => disconnect(btn.dataset.disconnect));
      });
    }

    async function connect(provider) {
      try {
        const { authorize_url } = await AgentOnAPI.get(`/platforms/${provider}/authorize`);
        window.location.href = authorize_url;
      } catch (err) {
        Toast.error(err.message);
      }
    }

    async function disconnect(provider) {
      try {
        await AgentOnAPI.del(`/platforms/${provider}`);
        Toast.info(`Disconnected ${provider}`);
        await refresh();
      } catch (err) {
        Toast.error(err.message);
      }
    }

    await refresh();
  }

  return { render };
})();
