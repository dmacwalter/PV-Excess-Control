/**
 * PV Excess Control - Lovelace Card Editor
 *
 * Provides a visual editor for configuring the PV Excess Control card
 * within the Home Assistant Lovelace UI editor.
 *
 * Uses Home Assistant's built-in Lit.
 */

// ---------------------------------------------------------------------------
// Resolve HA's built-in Lit
// ---------------------------------------------------------------------------
// Safely resolve HA's built-in Lit — never throw if unavailable
let LitElement, html, css;
try {
  const _getBase = (tag) => {
    const cls = customElements.get(tag);
    return cls ? Object.getPrototypeOf(cls) : undefined;
  };
  LitElement =
    _getBase("hui-masonry-view") ||
    _getBase("hui-view") ||
    _getBase("ha-panel-lovelace");
  if (LitElement && LitElement.prototype) {
    // Try prototype first, then the class itself (varies by HA version)
    html = LitElement.prototype.html || LitElement.html;
    css = LitElement.prototype.css || LitElement.css;
    // If still not found, try the parent prototype
    if (!html || !css) {
      const proto = Object.getPrototypeOf(LitElement);
      if (proto) {
        html = html || proto.html;
        css = css || proto.css;
      }
    }
  }
  if (!html || !css) LitElement = undefined;
} catch (e) {
  console.warn("PV Excess Control editor: Error resolving LitElement:", e);
  LitElement = undefined;
}

if (!LitElement) {
  // Can't define the editor without Lit — that's OK, the card still works
  // (HA shows the YAML editor as fallback)
}

// ---------------------------------------------------------------------------
// Editor options
// ---------------------------------------------------------------------------

if (LitElement) {

const TOGGLE_OPTIONS = [
  { key: "show_power_flow", label: "Show Power Flow" },
  { key: "show_appliances", label: "Show Appliances" },
  { key: "show_timeline", label: "Show Timeline" },
  { key: "show_forecast", label: "Show Forecast & Plan" },
  { key: "show_savings", label: "Show Savings Summary" },
  { key: "compact", label: "Compact Mode" },
];

// ---------------------------------------------------------------------------
// Editor element
// ---------------------------------------------------------------------------

class PvExcessCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      _config: { type: Object },
    };
  }

  setConfig(config) {
    this._config = {
      show_power_flow: true,
      show_appliances: true,
      show_timeline: true,
      show_forecast: true,
      show_savings: true,
      compact: false,
      ...config,
    };
  }

  render() {
    if (!this._config) return html``;

    return html`
      <div class="editor">
        <h3>PV Excess Control Card</h3>
        ${TOGGLE_OPTIONS.map(
          (opt) => html`
            <div class="toggle-row">
              <ha-switch
                .checked=${this._config[opt.key] !== false}
                @change=${(e) =>
                  this._valueChanged(opt.key, e.target.checked)}
              ></ha-switch>
              <label>${opt.label}</label>
            </div>
          `
        )}
        <p class="hint">
          In compact mode, timeline and forecast sections are hidden regardless
          of their individual toggle.
        </p>
      </div>
    `;
  }

  _valueChanged(key, value) {
    if (!this._config) return;

    const newConfig = { ...this._config, [key]: value };
    this._config = newConfig;

    const event = new CustomEvent("config-changed", {
      detail: { config: newConfig },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }

  static get styles() {
    return css`
      .editor {
        padding: 8px 0;
      }

      h3 {
        margin: 0 0 12px;
        font-size: 16px;
        font-weight: 500;
        color: var(--primary-text-color, #212121);
      }

      .toggle-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0;
      }

      .toggle-row label {
        font-size: 14px;
        color: var(--primary-text-color, #212121);
        cursor: pointer;
      }

      .hint {
        margin-top: 12px;
        font-size: 12px;
        color: var(--secondary-text-color, #727272);
        font-style: italic;
      }
    `;
  }
}

if (!customElements.get("pv-excess-card-editor")) {
  customElements.define("pv-excess-card-editor", PvExcessCardEditor);
}

} // end if (LitElement)
