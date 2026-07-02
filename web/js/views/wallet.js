const WalletView = (() => {
  function money(cents) {
    return `$${(cents / 100).toFixed(2)}`;
  }

  function kindLabel(kind) {
    return { recharge: "Recharge", order_payment: "Rental payment", consumption: "Usage", refund: "Refund" }[kind] || kind;
  }

  async function render(root) {
    root.innerHTML = `
      <div class="page-header">
        <div>
          <h1>Wallet</h1>
          <p>Fund your balance and track every charge.</p>
        </div>
      </div>
      <div class="stat-strip" id="wallet-stats"></div>
      <div class="card section-gap">
        <h3>Recharge</h3>
        <div class="actions-row" style="align-items:flex-end;">
          <div class="field" style="flex:1; min-width:160px; margin-bottom:0;">
            <label for="recharge-amount">Amount (USD)</label>
            <input type="number" id="recharge-amount" value="50" min="1" step="1" />
          </div>
          <button class="btn btn-primary" id="recharge-mock-btn">Recharge (dev)</button>
          <button class="btn btn-ghost" id="recharge-stripe-btn">Pay with card (Stripe)</button>
        </div>
        <label style="display:flex; align-items:center; gap: var(--space-2); margin-top: var(--space-5); font-size: var(--text-sm);">
          <input type="checkbox" id="auto-renew-toggle" />
          Auto-renew time-based rentals when they expire
        </label>
      </div>
      <h3>Transaction history</h3>
      <table class="table">
        <thead>
          <tr><th>Date</th><th>Type</th><th>Amount</th><th>Description</th></tr>
        </thead>
        <tbody id="tx-body"><tr><td colspan="4">Loading...</td></tr></tbody>
      </table>
    `;

    async function refresh() {
      try {
        const [wallet, txPage] = await Promise.all([AgentOnAPI.get("/billing/wallet"), AgentOnAPI.get("/billing/transactions")]);
        root.querySelector("#wallet-stats").innerHTML = `
          <div class="stat-box">
            <div class="stat-label">Balance</div>
            <div class="stat-value">${money(wallet.balance_cents)}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Status</div>
            <div class="stat-value">
              ${wallet.is_low_balance ? '<span class="badge badge-expired">Low balance</span>' : '<span class="badge badge-running">Healthy</span>'}
            </div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Auto-renew</div>
            <div class="stat-value">${wallet.auto_renew_enabled ? "On" : "Off"}</div>
          </div>
        `;
        root.querySelector("#auto-renew-toggle").checked = wallet.auto_renew_enabled;

        const rows = txPage.items
          .map(
            (tx) => `
          <tr>
            <td>${new Date(tx.created_at).toLocaleString()}</td>
            <td>${kindLabel(tx.kind)}</td>
            <td class="${tx.amount_cents >= 0 ? "amount-positive" : "amount-negative"}">${tx.amount_cents >= 0 ? "+" : ""}${money(tx.amount_cents)}</td>
            <td>${tx.description}</td>
          </tr>`
          )
          .join("");
        root.querySelector("#tx-body").innerHTML = rows || `<tr><td colspan="4">No transactions yet.</td></tr>`;
      } catch (err) {
        Toast.error(err.message);
      }
    }

    root.querySelector("#recharge-mock-btn").addEventListener("click", async () => {
      const amount = Math.round(Number(root.querySelector("#recharge-amount").value) * 100);
      try {
        await AgentOnAPI.post("/billing/wallet/recharge", { amount_cents: amount });
        Toast.info("Wallet recharged");
        await refresh();
      } catch (err) {
        Toast.error(err.message);
      }
    });

    root.querySelector("#recharge-stripe-btn").addEventListener("click", async () => {
      const amount = Math.round(Number(root.querySelector("#recharge-amount").value) * 100);
      try {
        const session = await AgentOnAPI.post("/billing/wallet/recharge/checkout", {
          amount_cents: amount,
          success_url: window.location.href,
          cancel_url: window.location.href,
        });
        window.location.href = session.checkout_url;
      } catch (err) {
        Toast.error(err.message.includes("does not support") ? "Set PAYMENT_PROVIDER=stripe on the server to enable this." : err.message);
      }
    });

    root.querySelector("#auto-renew-toggle").addEventListener("change", async (e) => {
      try {
        await AgentOnAPI.patch("/billing/wallet/settings", { auto_renew_enabled: e.target.checked });
        Toast.info(e.target.checked ? "Auto-renew enabled" : "Auto-renew disabled");
      } catch (err) {
        Toast.error(err.message);
        e.target.checked = !e.target.checked;
      }
    });

    await refresh();
  }

  return { render };
})();
