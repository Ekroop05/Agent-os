import { useEffect, useState } from "react";

const defaults = {
  apiUrl: "http://127.0.0.1:8000",
  wsUrl: "ws://localhost:8000",
  theme: "Dark command center",
  animationLevel: "Balanced",
  headModel: "qwen3:14b",
  builderModel: "qwen2.5-coder:7b",
  securityModel: "qwen2.5-coder:7b",
};

export default function Settings() {
  const [settings, setSettings] = useState(() => ({
    apiUrl: localStorage.getItem("agentos.apiUrl") || defaults.apiUrl,
    wsUrl: localStorage.getItem("agentos.wsUrl") || defaults.wsUrl,
    theme: localStorage.getItem("agentos.theme") || defaults.theme,
    animationLevel: localStorage.getItem("agentos.animationLevel") || defaults.animationLevel,
    headModel: localStorage.getItem("agentos.headModel") || defaults.headModel,
    builderModel: localStorage.getItem("agentos.builderModel") || defaults.builderModel,
    securityModel: localStorage.getItem("agentos.securityModel") || defaults.securityModel,
  }));

  useEffect(() => {
    Object.entries(settings).forEach(([key, value]) => {
      localStorage.setItem(`agentos.${key}`, value);
    });
  }, [settings]);

  function update(key, value) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="settings-grid">
      <SettingsPanel title="System Configuration">
        <SettingInput label="Backend URL" value={settings.apiUrl} onChange={(value) => update("apiUrl", value)} />
        <SettingInput label="WebSocket URL" value={settings.wsUrl} onChange={(value) => update("wsUrl", value)} />
      </SettingsPanel>

      <SettingsPanel title="Default Models">
        <SettingInput label="Head Agent Model" value={settings.headModel} onChange={(value) => update("headModel", value)} />
        <SettingInput label="Builder Agent Model" value={settings.builderModel} onChange={(value) => update("builderModel", value)} />
        <SettingInput label="Security Agent Model" value={settings.securityModel} onChange={(value) => update("securityModel", value)} />
      </SettingsPanel>

      <SettingsPanel title="Appearance">
        <SettingInput label="Theme" value={settings.theme} onChange={(value) => update("theme", value)} />
        <label className="setting-row">
          <span>Animation Settings</span>
          <select value={settings.animationLevel} onChange={(event) => update("animationLevel", event.target.value)}>
            <option>Reduced</option>
            <option>Balanced</option>
            <option>Full</option>
          </select>
        </label>
      </SettingsPanel>

      <SettingsPanel title="Developer Options">
        <SettingInput label="Event Logging" value="Enabled" readOnly />
        <SettingInput label="Performance Metrics" value="Enabled" readOnly />
        <SettingInput label="Debug Mode" value="Enabled" readOnly />
      </SettingsPanel>
    </div>
  );
}

function SettingsPanel({ title, children }) {
  return (
    <section className="panel settings-panel">
      <div className="section-heading">
        <h2>{title}</h2>
        <span>Saved</span>
      </div>
      {children}
    </section>
  );
}

function SettingInput({ label, value, onChange, readOnly = false }) {
  return (
    <label className="setting-row">
      <span>{label}</span>
      <input readOnly={readOnly} value={value} onChange={(event) => onChange?.(event.target.value)} />
    </label>
  );
}
