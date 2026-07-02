const InstancesView = (() => {
  function escapeHtml(str) {
    return (str || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function actionsFor(instance) {
    const actions = [];
    if (instance.status === "created" || instance.status === "paused") {
      actions.push(`<button class="btn btn-sm btn-primary" data-action="start">Start</button>`);
    }
    if (instance.status === "running") {
      actions.push(`<button class="btn btn-sm btn-ghost" data-action="execute">Run task</button>`);
      actions.push(`<button class="btn btn-sm btn-ghost" data-action="pause">Pause</button>`);
      actions.push(`<button class="btn btn-sm btn-ghost" data-action="stop">Stop</button>`);
    }
    if (instance.status === "stopped" || instance.status === "expired") {
      actions.push(`<button class="btn btn-sm btn-danger" data-action="release">Release</button>`);
    }
    return actions.join("");
  }

  async function render(root) {
    root.innerHTML = `
      <div class="page-header">
        <div>
          <h1>My Instances</h1>
          <p>Manage every agent you've rented — start, run, and retire them.</p>
        </div>
        <button class="btn btn-ghost" id="refresh-btn">Refresh</button>
      </div>
      <div id="instance-list"></div>
    `;

    const list = root.querySelector("#instance-list");

    async function refresh() {
      list.innerHTML = `<div class="empty-state">Loading...</div>`;
      try {
        const instances = await AgentOnAPI.get("/instances");
        if (!instances.length) {
          list.innerHTML = `<div class="empty-state">No instances yet — rent an agent from the <a href="#/marketplace">Marketplace</a> to get started.</div>`;
          return;
        }
        list.innerHTML = instances
          .map(
            (i) => `
          <div class="card section-gap" data-id="${i.id}">
            <div class="page-header" style="margin-bottom: var(--space-3);">
              <div>
                <span class="badge badge-${i.status}">${escapeHtml(i.status)}</span>
                <span class="mono" style="color: var(--color-text-faint); margin-left: var(--space-2);">${i.id.slice(0, 12)}</span>
              </div>
              <div class="actions-row">${actionsFor(i)}</div>
            </div>
            <div class="stat-strip" style="margin-bottom:0;">
              <div class="stat-box">
                <div class="stat-label">Pricing</div>
                <div class="stat-value" style="font-size: var(--text-lg);">${escapeHtml(i.pricing_unit)}</div>
              </div>
              <div class="stat-box">
                <div class="stat-label">Fail streak</div>
                <div class="stat-value" style="font-size: var(--text-lg);">${i.fail_streak}</div>
              </div>
              <div class="stat-box">
                <div class="stat-label">Last run</div>
                <div class="stat-value" style="font-size: var(--text-lg);">${i.last_run_at ? new Date(i.last_run_at).toLocaleString() : "never"}</div>
              </div>
            </div>
            ${i.last_result_message ? `<p style="margin-top: var(--space-4);"><strong>Last result:</strong> ${escapeHtml(i.last_result_message)}</p>` : ""}
            ${i.auto_paused_reason ? `<p style="color: var(--color-danger);">${escapeHtml(i.auto_paused_reason)}</p>` : ""}
          </div>`
          )
          .join("");

        list.querySelectorAll("[data-action]").forEach((btn) => {
          btn.addEventListener("click", () => runAction(btn.closest(".card").dataset.id, btn.dataset.action));
        });
      } catch (err) {
        list.innerHTML = `<div class="empty-state">Failed to load instances.</div>`;
        Toast.error(err.message);
      }
    }

    async function runAction(instanceId, action) {
      try {
        if (action === "execute") {
          const result = await AgentOnAPI.post(`/instances/${instanceId}/execute`, {});
          Toast.info(result.success ? `Task done: ${result.message}` : `Task failed: ${result.message}`);
        } else {
          await AgentOnAPI.post(`/instances/${instanceId}/${action}`);
          Toast.info(`Instance ${action}ed`);
        }
        await refresh();
      } catch (err) {
        Toast.error(err.message);
      }
    }

    root.querySelector("#refresh-btn").addEventListener("click", refresh);
    await refresh();
  }

  return { render };
})();
