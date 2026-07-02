const AgentOnAPI = (() => {
  const TOKEN_KEY = "agenton_token";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  }

  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  }

  function isAuthenticated() {
    return Boolean(getToken());
  }

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.status = status;
    }
  }

  async function request(path, { method = "GET", body, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth && getToken()) headers.Authorization = `Bearer ${getToken()}`;

    const resp = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (resp.status === 401 && auth) {
      clearToken();
      window.location.hash = "#/login";
    }

    if (resp.status === 204) return null;

    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new ApiError(data.detail || `Request failed (${resp.status})`, resp.status);
    }
    return data;
  }

  return {
    getToken,
    setToken,
    clearToken,
    isAuthenticated,
    ApiError,
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body }),
    patch: (path, body) => request(path, { method: "PATCH", body }),
    del: (path) => request(path, { method: "DELETE" }),
    register: (email, password, displayName) =>
      request("/auth/register", { method: "POST", body: { email, password, display_name: displayName }, auth: false }),
    login: (email, password) => request("/auth/login", { method: "POST", body: { email, password }, auth: false }),
    me: () => request("/auth/me"),
  };
})();
