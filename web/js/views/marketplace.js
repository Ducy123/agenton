const MarketplaceView = (() => {
  function escapeHtml(str) {
    return (str || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function priceLabel(cents, unit) {
    const amount = (cents / 100).toFixed(2);
    const suffix = { hour: "/ hr", day: "/ day", month: "/ mo", token: "/ run", package: "/ pkg" }[unit] || "";
    return `$${amount} <small>${suffix}</small>`;
  }

  async function render(root) {
    root.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Agent Marketplace</h1>
          <p>Rent an AI agent, connect your accounts, and put it to work.</p>
        </div>
        <button class="btn btn-primary" id="publish-btn">+ Publish agent</button>
      </div>
      <div class="actions-row section-gap">
        <input type="search" id="search-input" placeholder="Search agents..." style="flex:1; min-width:220px; padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); border:1px solid var(--color-border);" />
        <select id="category-select" style="padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); border:1px solid var(--color-border);">
          <option value="">All categories</option>
        </select>
      </div>
      <div id="agent-grid" class="bento-grid"><div class="empty-state">Loading...</div></div>
    `;

    const grid = root.querySelector("#agent-grid");
    const searchInput = root.querySelector("#search-input");
    const categorySelect = root.querySelector("#category-select");

    async function loadCategories() {
      try {
        const categories = await AgentOnAPI.get("/marketplace/categories");
        categorySelect.innerHTML =
          `<option value="">All categories</option>` + categories.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
      } catch (err) {
        Toast.error(err.message);
      }
    }

    async function loadAgents() {
      grid.innerHTML = `<div class="empty-state">Loading...</div>`;
      const params = new URLSearchParams();
      if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
      if (categorySelect.value) params.set("category", categorySelect.value);
      try {
        const page = await AgentOnAPI.get(`/marketplace/agents?${params.toString()}`);
        if (!page.items.length) {
          grid.innerHTML = `<div class="empty-state">No agents match your search yet.</div>`;
          return;
        }
        grid.innerHTML = page.items
          .map(
            (a) => `
          <div class="agent-card" data-id="${a.id}">
            <div class="agent-card-icon">${escapeHtml(a.name.slice(0, 1).toUpperCase())}</div>
            <h3 class="agent-card-title">${escapeHtml(a.name)}</h3>
            <p class="agent-card-desc">${escapeHtml(a.short_description || "No description yet.")}</p>
            <div class="agent-card-footer">
              <span class="badge" style="background: var(--color-info-soft); color: var(--color-info);">${escapeHtml(a.category)}</span>
              <span class="price-tag">${priceLabel(a.base_price_cents, a.pricing_unit)}</span>
            </div>
          </div>`
          )
          .join("");
        grid.querySelectorAll(".agent-card").forEach((card) => {
          card.addEventListener("click", () => openDetail(card.dataset.id));
        });
      } catch (err) {
        grid.innerHTML = `<div class="empty-state">Failed to load agents.</div>`;
        Toast.error(err.message);
      }
    }

    searchInput.addEventListener("input", debounce(loadAgents, 300));
    categorySelect.addEventListener("change", loadAgents);
    root.querySelector("#publish-btn").addEventListener("click", () => openPublishForm(loadAgents));

    await loadCategories();
    await loadAgents();
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  function openOverlay(contentHtml) {
    const overlay = document.createElement("div");
    overlay.className = "overlay";
    overlay.innerHTML = `<div class="panel">${contentHtml}</div>`;
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.remove();
    });
    document.body.appendChild(overlay);
    return overlay;
  }

  async function openDetail(templateId) {
    let agent;
    try {
      agent = await AgentOnAPI.get(`/marketplace/agents/${templateId}`);
    } catch (err) {
      Toast.error(err.message);
      return;
    }

    const overlay = openOverlay(`
      <button class="panel-close" data-close>&times;</button>
      <h2 style="margin-top: var(--space-8)">${escapeHtml(agent.name)}</h2>
      <span class="badge" style="background: var(--color-info-soft); color: var(--color-info); margin-bottom: var(--space-4); display:inline-flex;">${escapeHtml(agent.category)}</span>
      <p>${escapeHtml(agent.long_description || agent.short_description || "No description provided.")}</p>
      <div class="stat-box section-gap">
        <div class="stat-label">Price</div>
        <div class="stat-value">${priceLabel(agent.base_price_cents, agent.pricing_unit)}</div>
      </div>
      <h4>Rent this agent</h4>
      <div class="field">
        <label for="rent-quantity">Quantity (${escapeHtml(agent.pricing_unit)})</label>
        <input type="number" id="rent-quantity" value="1" min="1" />
      </div>
      <div class="field">
        <label for="rent-params">Task parameters (JSON, optional)</label>
        <textarea id="rent-params" rows="4" placeholder='{"url": "https://example.com"}'></textarea>
        <span class="field-hint">Depends on the task type this agent runs — see the agent's docs.</span>
      </div>
      <button class="btn btn-primary btn-block" id="rent-btn">Rent &amp; activate</button>
    `);

    overlay.querySelector("[data-close]").addEventListener("click", () => overlay.remove());
    overlay.querySelector("#rent-btn").addEventListener("click", async () => {
      const quantity = Number(overlay.querySelector("#rent-quantity").value) || 1;
      const rawParams = overlay.querySelector("#rent-params").value.trim();
      let taskParams = {};
      if (rawParams) {
        try {
          taskParams = JSON.parse(rawParams);
        } catch {
          Toast.error("Task parameters must be valid JSON");
          return;
        }
      }
      try {
        const order = await AgentOnAPI.post("/billing/orders", { template_id: agent.id, quantity });
        await AgentOnAPI.post(`/billing/orders/${order.id}/pay`);
        await AgentOnAPI.post("/instances", { order_id: order.id, task_params: taskParams });
        Toast.info("Agent rented — starting it now in My Instances");
        overlay.remove();
        window.location.hash = "#/instances";
      } catch (err) {
        Toast.error(err.message);
      }
    });
  }

  function openPublishForm(onDone) {
    const overlay = openOverlay(`
      <button class="panel-close" data-close>&times;</button>
      <h2 style="margin-top: var(--space-8)">Publish an agent</h2>
      <p>List a new agent template for renters to discover.</p>
      <div class="field">
        <label for="p-name">Name</label>
        <input type="text" id="p-name" required />
      </div>
      <div class="field">
        <label for="p-slug">Slug</label>
        <input type="text" id="p-slug" placeholder="my-agent" required />
      </div>
      <div class="field">
        <label for="p-category">Category</label>
        <input type="text" id="p-category" placeholder="growth" required />
      </div>
      <div class="field">
        <label for="p-task-type">Task type</label>
        <select id="p-task-type">
          <option value="webvisit">webvisit</option>
          <option value="ai_content_generation">ai_content_generation</option>
          <option value="twitter_follow">twitter_follow</option>
          <option value="twitter_like">twitter_like</option>
          <option value="twitter_retweet">twitter_retweet</option>
          <option value="twitter_post">twitter_post</option>
          <option value="discord_join">discord_join</option>
          <option value="platform_register">platform_register</option>
        </select>
      </div>
      <div class="field">
        <label for="p-desc">Short description</label>
        <input type="text" id="p-desc" />
      </div>
      <div class="field">
        <label for="p-price">Price (cents)</label>
        <input type="number" id="p-price" value="100" min="0" required />
      </div>
      <div class="field">
        <label for="p-unit">Pricing unit</label>
        <select id="p-unit">
          <option value="token">token (per run)</option>
          <option value="hour">hour</option>
          <option value="day">day</option>
          <option value="month">month</option>
          <option value="package">package</option>
        </select>
      </div>
      <button class="btn btn-primary btn-block" id="publish-submit">Publish</button>
    `);

    overlay.querySelector("[data-close]").addEventListener("click", () => overlay.remove());
    overlay.querySelector("#publish-submit").addEventListener("click", async () => {
      const payload = {
        name: overlay.querySelector("#p-name").value.trim(),
        slug: overlay.querySelector("#p-slug").value.trim(),
        category: overlay.querySelector("#p-category").value.trim(),
        task_type: overlay.querySelector("#p-task-type").value,
        short_description: overlay.querySelector("#p-desc").value.trim(),
        base_price_cents: Number(overlay.querySelector("#p-price").value),
        pricing_unit: overlay.querySelector("#p-unit").value,
      };
      try {
        await AgentOnAPI.post("/marketplace/agents", payload);
        Toast.info("Agent published");
        overlay.remove();
        onDone?.();
      } catch (err) {
        Toast.error(err.message);
      }
    });
  }

  return { render };
})();
