(() => {
  const mockConfig = {
    appMode: "static-skeleton",
    zdocService: "not-started-by-this-app",
    kgAccess: "disabled",
    projectDataAccess: "disabled",
    generation: "disabled",
    export: "disabled",
    writeBack: "disabled"
  };

  const actionNotice = document.getElementById("actionNotice");
  const mockConfigView = document.getElementById("mockConfig");
  const noopButtons = document.querySelectorAll("[data-noop]");
  const tabButtons = document.querySelectorAll("[data-panel-target]");

  if (mockConfigView) {
    mockConfigView.textContent = JSON.stringify(mockConfig, null, 2);
  }

  noopButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!actionNotice) {
        return;
      }

      const label = button.textContent.trim();
      actionNotice.textContent = `未授权，不执行真实动作：${label}`;
    });
  });

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.panelTarget;

      tabButtons.forEach((item) => {
        const selected = item === button;
        item.classList.toggle("is-active", selected);
        item.setAttribute("aria-selected", String(selected));
      });

      document.querySelectorAll(".panel").forEach((panel) => {
        const selected = panel.id === targetId;
        panel.classList.toggle("is-active", selected);
        panel.hidden = !selected;
      });
    });
  });
})();
