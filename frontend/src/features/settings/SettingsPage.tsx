import type { ThemePreference } from "../../appearance";
import { Icon, type IconName } from "../../components/Icon";

const choices: { id: ThemePreference; label: string; description: string; icon: IconName }[] = [
  { id: "light", label: "Light", description: "Use a light workspace.", icon: "light" },
  { id: "dark", label: "Dark", description: "Use a low-glare dark workspace.", icon: "dark" },
  { id: "system", label: "System", description: "Follow your operating system.", icon: "system" },
];

export function SettingsPage({ theme, onThemeChange }: { theme: ThemePreference; onThemeChange: (value: ThemePreference) => void }) {
  return <section className="settings-page">
    <header className="section-heading"><div><p className="eyebrow">Application</p><h1>Settings</h1><p>Make the workspace comfortable for your screen.</p></div></header>
    <section className="settings-section" aria-labelledby="appearance-title">
      <div className="settings-section-heading"><h2 id="appearance-title">Appearance</h2><p>Choose a theme. Changes take effect immediately.</p></div>
      <fieldset className="theme-choices"><legend className="visually-hidden">Appearance theme</legend>
        {choices.map((choice) => <label key={choice.id} className="theme-choice">
          <input type="radio" name="appearance" value={choice.id} checked={theme === choice.id} onChange={() => onThemeChange(choice.id)} />
          <Icon name={choice.icon} size={20} /><span><strong>{choice.label}</strong><small>{choice.description}</small></span>
        </label>)}
      </fieldset>
    </section>
  </section>;
}
