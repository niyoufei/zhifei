(() => {
  const mockConfig = {
    appMode: "professional-static-console",
    node: "LOCAL-LAUNCHER-017-R1",
    authorization: "not-authorized-to-run",
    runtimeMode: "no-service-no-endpoint",
    permissions: {
      serviceLifecycle: false,
      networkAccess: false,
      endpointAccess: false,
      ollamaAccess: false,
      modelInference: false,
      promptInput: false,
      realKgRead: false,
      projectDataRead: false,
      secretRead: false,
      logBodyRead: false,
      outputJobExportRead: false,
      generation: false,
      export: false,
      writeBack: false,
      trialUse: false,
      realUse: false,
      fiftyPersonUse: false
    },
    status: {
      zdocService: "mock-not-started",
      ollamaServer: "mock-not-connected",
      logs: "read-blocked",
      ports: "check-disabled",
      config: "real-config-read-disabled"
    }
  };

  const actionNotice = document.getElementById("actionNotice");
  const mockConfigView = document.getElementById("mockConfig");
  const noopButtons = document.querySelectorAll("[data-noop]");
  const panelButtons = document.querySelectorAll("[data-panel-target]");
  const panels = document.querySelectorAll("[role='tabpanel']");
  const noopMessages = {
    "启动": "静态 no-op：启动入口已禁用；页面不启动任何服务。",
    "停止": "静态 no-op：停止入口已禁用；页面不停止或重启任何进程。",
    "刷新状态": "静态 no-op：状态刷新已禁用；页面不检查真实运行状态。",
    "读取日志": "静态 no-op：日志读取已禁用；页面不读取日志正文。",
    "检查端口": "静态 no-op：端口检查已禁用；页面不探测端口或环境。",
    "查看配置": "静态 no-op：配置查看已禁用；页面不读取真实配置。"
  };

  const setNotice = (message) => {
    if (actionNotice) {
      actionNotice.textContent = message;
    }
  };

  if (mockConfigView) {
    mockConfigView.textContent = JSON.stringify(mockConfig, null, 2);
  }

  noopButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const label = button.dataset.noop || button.textContent.trim();
      setNotice(noopMessages[label] || `静态 no-op：${label} 未授权执行。`);
    });
  });

  panelButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = `panel-${button.dataset.panelTarget}`;

      panelButtons.forEach((item) => {
        const selected = item === button;
        item.classList.toggle("is-active", selected);
        item.setAttribute("aria-selected", String(selected));
      });

      panels.forEach((panel) => {
        const selected = panel.id === targetId;
        panel.classList.toggle("is-active", selected);
        panel.hidden = !selected;
      });

      setNotice("静态 no-op：仅切换页面内说明面板，不读取文件、不访问网络、不触发真实动作。");
    });
  });
})();
