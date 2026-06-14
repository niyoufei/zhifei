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
  const noopMessages = {
    启动提示: "静态 no-op：未授权启动；页面只保留按钮位置。",
    停止提示: "静态 no-op：未授权停止；页面不控制任何进程。",
    状态提示: "静态 no-op：未授权检测状态；页面只显示 mock 状态。",
    日志提示: "静态 no-op：未授权读取日志；页面不读取任何正文。",
    端口提示: "静态 no-op：未授权检查端口；页面不探测运行环境。",
    配置提示: "静态 no-op：未授权读取配置；页面只展示内置 mock 状态。"
  };

  if (mockConfigView) {
    mockConfigView.textContent = JSON.stringify(mockConfig, null, 2);
  }

  noopButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!actionNotice) {
        return;
      }

      const label = button.dataset.noop || button.textContent.trim();
      actionNotice.textContent = noopMessages[label] || `静态 no-op：未授权执行 ${label}。`;
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
