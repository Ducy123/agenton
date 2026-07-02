const Toast = (() => {
  let stack;

  function ensureStack() {
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      document.body.appendChild(stack);
    }
    return stack;
  }

  function show(message, { error = false, duration = 3200 } = {}) {
    const el = document.createElement("div");
    el.className = "toast" + (error ? " toast-error" : "");
    el.textContent = message;
    ensureStack().appendChild(el);
    setTimeout(() => el.remove(), duration);
  }

  return {
    info: (message) => show(message),
    error: (message) => show(message, { error: true }),
  };
})();
