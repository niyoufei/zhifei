(() => {
  const mockConfig = {
    appMode: "static-skeleton",
    zdocService: "not-started-by-this-app",
    runtimeAccess: "disabled",
    networkAccess: "disabled",
    kgAccess: "disabled",
    projectDataAccess: "disabled",
    secretAccess: "disabled",
    generation: "disabled",
    export: "disabled",
    writeBack: "disabled",
    trialUse: "blocked"
  };

  const actionNotice = document.getElementById("actionNotice");
  const mockConfigView = document.getElementById("mockConfig");
  const noopButtons = document.querySelectorAll("[data-noop]");
  const tabButtons = document.querySelectorAll("[data-panel-target]");
  const noopMessages = {
    "启动 no-op": "静态 no-op：启动入口已禁用；页面只更新提示，不启动任何服务。",
    "停止 no-op": "静态 no-op：停止入口已禁用；页面不停止或重启任何进程。",
    "状态 no-op": "静态 no-op：状态检查已禁用；页面只展示 mock 状态。",
    "日志 no-op": "静态 no-op：日志读取已禁用；页面不读取任何正文。",
    "端口 no-op": "静态 no-op：端口检查已禁用；页面不探测运行环境。",
    "配置 no-op": "静态 no-op：配置读取已禁用；页面只展示内置 mock 状态。"
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
