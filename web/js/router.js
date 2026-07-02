const Router = (() => {
  const routes = [];
  let mountPoint;

  function register(pattern, render, { requiresAuth = true } = {}) {
    const paramNames = [];
    const regex = new RegExp(
      "^" +
        pattern.replace(/:[^/]+/g, (match) => {
          paramNames.push(match.slice(1));
          return "([^/]+)";
        }) +
        "$"
    );
    routes.push({ regex, paramNames, render, requiresAuth });
  }

  function currentPath() {
    return (window.location.hash || "#/").slice(1) || "/";
  }

  async function resolve() {
    const path = currentPath();
    const match = routes.find((r) => r.regex.test(path));

    if (!match) {
      window.location.hash = AgentOnAPI.isAuthenticated() ? "#/marketplace" : "#/login";
      return;
    }

    if (match.requiresAuth && !AgentOnAPI.isAuthenticated()) {
      window.location.hash = "#/login";
      return;
    }

    if (!match.requiresAuth && AgentOnAPI.isAuthenticated() && (path === "/login" || path === "/register")) {
      window.location.hash = "#/marketplace";
      return;
    }

    const values = match.regex.exec(path).slice(1);
    const params = Object.fromEntries(match.paramNames.map((name, i) => [name, values[i]]));

    document.dispatchEvent(new CustomEvent("agenton:navigate", { detail: { path, requiresAuth: match.requiresAuth } }));
    mountPoint.innerHTML = "";
    await match.render(mountPoint, params);
  }

  function init(el) {
    mountPoint = el;
    window.addEventListener("hashchange", resolve);
    resolve();
  }

  return { register, init, resolve, currentPath };
})();
